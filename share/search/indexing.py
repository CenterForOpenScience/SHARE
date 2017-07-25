import collections
import logging
import itertools

from django.apps import apps
from django.conf import settings

from share import util
from share.models.base import ShareObject
from share.search.fetchers import fetcher_for

logger = logging.getLogger(__name__)


class FakeMessage:

    def __init__(self, model, ids):
        self.ids = ids
        self.model = model
        self.payload = {model: ids}

    def ack(self):
        return True

    def requeue(self):
        return True


class IndexableMessage:
    PROTOCOL_VERSION = None

    @classmethod
    def wrap(cls, message):
        version = message.payload.get('version', 0)
        for klass in cls.__subclasses__():
            if klass.PROTOCOL_VERSION == version:
                return klass(message)
        raise ValueError('Invalid version "{}"'.format(version))

    @property
    def model(self):
        # You can't override properties with attributes
        # This allows subclasses to just set _model in __init__
        # rather than have to override .model
        if not hasattr(self, '_model'):
            raise NotImplementedError
        return self._model

    def __init__(self, message):
        self.message = message
        self.protocol_version = message.payload.get('version', 0)

    def ack(self):
        return self.message.ack()

    def requeue(self):
        return self.message.reject_log_error(logger, Exception, requeue=True)

    def malformed(self, reason):
        raise ValueError('Malformed version {} payload, {}: {!r}'.format(
            self.PROTOCOL_VERSION,
            reason,
            self.message.payload,
        ))

    def iter_ids(self):
        raise NotImplementedError

    def __iter__(self):
        for id in self.iter_ids():
            yield id

    def _to_model(self, name):
        name = name.lower()

        if name.startswith('share.'):
            model = apps.get_model(name)
        else:
            model = apps.get_model('share', name)

        if not issubclass(model, ShareObject):
            raise ValueError('Invalid model "{!r}"'.format(model))

        # Kinda a hack, grab the first non-abstract version of a typed model
        if model._meta.concrete_model.__subclasses__():
            return model._meta.concrete_model.__subclasses__()[0]

        return model


class V0Message(IndexableMessage):
    """
    {
        "<model_name>": [id1, id2, id3...]
    }
    """
    PROTOCOL_VERSION = 0

    def __init__(self, message):
        super().__init__(message)

        self.message.payload.pop('version', None)

        if len(self.message.payload.keys()) > 1:
            raise self.malformed('Multiple models')

        ((model, ids), ) = tuple(self.message.payload.items())

        self.ids = ids
        self._model = self._to_model(model)

    def iter_ids(self):
        return iter(self.ids)

    def __len__(self):
        return len(self.ids)


class V1Message(IndexableMessage):
    """
    {
        "version": 1,
        "model": "<model_name>",
        "ids": [id1, id2, id3...],
        "indexes": [share_v1, share_v2...],
    }
    """
    PROTOCOL_VERSION = 1

    @property
    def model(self):
        return self._to_model(self.message.payload['model'])

    @property
    def indexes(self):
        return self.message.payload.get('indexes', [settings.ELASTICSEARCH['ACTIVE_INDEXES']])

    def iter_ids(self):
        return iter(self.message.payload['ids'])

    def __len__(self):
        return len(self.message.payload['ids'])


# TODO Better Name
class ChunkedFlattener:

    def __init__(self, index, model, messages, counter, size=500):
        self._counter = counter
        self._index = index
        self._messages = messages
        self._model = model
        self._size = 500

        if index not in settings.ELASTICSEARCH['INDEXES']:
            overrides = None
        else:
            overrides = settings.ELASTICSEARCH['INDEXES'][index].get('FETCHERS')

        self._fetcher = fetcher_for(model, overrides)

    def __iter__(self):
        opts = {'_index': self._index, '_type': self._model._meta.verbose_name_plural.replace(' ', '')}
        for chunk in util.chunked(self._flatten(), size=250):
            for result in self._fetcher(chunk):
                if result is None:
                    continue
                if result.pop('is_deleted', False):
                    yield {'_id': result['id'], '_op_type': 'delete', **opts}
                else:
                    yield {'_id': result['id'], '_op_type': 'index', **opts, **result}

    def _flatten(self):
        for message in self._messages:
            self._counter[message] += 1
            for _id in message:
                yield _id
            self._counter[message] -= 1


class ElasticsearchActionGenerator:

    def __init__(self, indexes, messages):
        self.indexes = indexes
        self.acked = collections.deque()
        self.pending = collections.deque()

        self.messages = tuple(sorted((
            IndexableMessage.wrap(message)
            for message in messages
        ), key=lambda msg: msg.model._meta.model_name))

    def ack_pending(self):
        while self.pending:
            msg = self.pending.pop()
            msg.ack()
            self.acked.append(msg)

    def requeue(self):
        count = 0
        for message in self.messages:
            if not message.message.acknowledged:
                message.requeue()
                count += 1
        return count

    def __len__(self):
        return sum(len(x) for x in self.messages)

    def __iter__(self):
        for model, messages in itertools.groupby(self.messages, lambda msg: msg.model):
            messages = tuple(messages)
            counter = collections.Counter()

            streams = []
            for index in self.indexes:
                streams.append(ChunkedFlattener(index, model, messages, counter))

            for result in util.interweave(*streams):
                for message, count in tuple(counter.items()):
                    if count < 1:
                        self.pending.append(message)
                        del counter[message]

                yield result

            for message, count in tuple(counter.items()):
                if count < 1:
                    self.pending.append(message)
                    del counter[message]
