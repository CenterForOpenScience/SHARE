import time
import collections
import logging

from elasticsearch import helpers

from django.apps import apps

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

    def malformed(self, reason):
        raise ValueError('Malformed version {} payload, {}: {!r}'.format(
            self.PROTOCOL_VERSION,
            reason,
            self.message.payload,
        ))

    def __iter__(self):
        raise NotImplementedError

    def __next__(self):
        raise NotImplementedError

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

    def __len__(self):
        return len(self.ids)

    def __iter__(self):
        return iter(self.ids)


class V1Message(IndexableMessage):
    """
    {
        "version": 1,
        "model": "<model_name>",
        "ids": [id1, id2, id3...]
    }
    """
    PROTOCOL_VERSION = 1

    @property
    def model(self):
        return self._to_model(self.message.payload['model'])

    def __iter__(self):
        return iter(self.message.payload['ids'])

    def __len__(self):
        return len(self.message.payload['ids'])


class MessageFlattener:

    def __init__(self, messages):
        self.acked = []
        self.pending = []
        self.requeued = []

        self.current = None
        self.messages = collections.deque(messages)
        self.buffer = collections.deque()

    def ack_pending(self):
        if not self.pending:
            return

        for message in self.pending:
            message.message.ack()
            self.acked.append(message)

        self.pending.clear()

    def requeue_pending(self):
        if not self.pending:
            return

        for message in self.pending:
            message.message.requeue()
            self.requeued.append(message)

        self.pending.clear()

    def reset_pending(self):
        if not self.pending:
            return

        for message in self.pending:
            self.messages.append(message)

        self.current = None
        self.pending.clear()

    def __len__(self):
        return sum([len(msg) for msg in self.messages], 0)

    def __iter__(self):
        if self.current is None:
            self._load_buffer()
        return self

    def __next__(self):
        self._load_buffer()

        try:
            return self.buffer.popleft()
        except IndexError:
            raise StopIteration

    def _load_buffer(self):
        while True:
            if self.current is None and not self.messages:
                return

            if self.current is None:
                self.current = iter(self.messages[0])

            try:
                self.buffer.append(next(self.current))
            except StopIteration:
                self.current = None
                self.pending.append(self.messages.popleft())
            else:
                return


class ESIndexer:

    MAX_RETRIES = 10
    CHUNK_SIZE = 500
    MAX_CHUNK_BYTES = 32 * 10124 ** 2
    GENTLE_SLEEP_TIME = 5  # seconds

    def __init__(self, client, index, *messages):
        self.client = client
        self.indexables = {}
        self.es_index = index
        self.retries = 0

        # Sort messages by types
        for message in messages:
            message = IndexableMessage.wrap(message)
            if message.model not in self.indexables:
                self.indexables[message.model] = MessageFlattener([])
            self.indexables[message.model].messages.append(message)

    def index(self):
        self.retries = 0

        logger.debug('Starting indexing')

        while True:
            try:
                return self._index()
            except Exception as e:
                logger.exception('Indexing Failed')

                self.retries += 1

                if self.retries >= self.MAX_RETRIES:
                    logger.critical('Unable to continue indexing after %d attempts. Giving up...', self.retries)
                    raise SystemExit(1)

                timeout = 2 ** self.retries
                logger.warning('Backing off for %d seconds', timeout)
                time.sleep(timeout)
                logger.info('Woke up, continuing indexing')

    def _index(self):
        logger.info('Checking that ES health is yellow or above')
        status = self.client.cluster.health(wait_for_status='yellow')

        gentle = False
        if status['status'] == 'red':
            raise ValueError('ES cluster health is red, Refusing to index')

        if status['status'] == 'yellow':
            logger.warning('ES cluster health is yellow, enabling gentle mode')
            gentle = True

        # TODO Check for pending indexing tasks and enable gentleness

        for model, flattener in self.indexables.items():

            # If we are re-entering due to a retry, reset out iterators
            # to move any pending ids to the back of the line
            flattener.reset_pending()

            if len(flattener) < 1:
                logger.debug('%s is empty, skipping...', model)
                continue

            logger.info('Indexing %s %s(s)', len(flattener), model)

            streamer = helpers.streaming_bulk(
                self.client,
                self.bulk_stream(model, flattener, self.es_index, gentle=gentle),
                max_chunk_bytes=self.MAX_CHUNK_BYTES,
                raise_on_error=True
            )

            for ok, resp in streamer:
                if not ok and not (resp.get('delete') and resp['delete']['status'] == 404):
                    raise ValueError(resp)

                # ACK messages ASAP to avoid an infinite loop of re-indexing the same
                # documents over and over
                # By the time we actually get here, we know that ES has ingested this/these docs
                # so it's safe to ACK them
                flattener.ack_pending()

    def bulk_stream(self, model, flattener, index, gentle=False):
        fetcher = fetcher_for(model)
        opts = {'_index': index, '_type': model._meta.verbose_name_plural.replace(' ', '')}

        for chunk in util.chunked(flattener, size=self.CHUNK_SIZE):
            logger.debug('Indexing a chunk of size %d', len(chunk))
            for blob in fetcher(chunk):
                if blob.pop('is_deleted', False):
                    yield {'_id': blob['id'], '_op_type': 'delete', **opts}
                else:
                    yield {'_id': blob['id'], '_op_type': 'index', **blob, **opts}
            if gentle:
                logger.debug('Gentle mode enabled, sleeping for %d seconds', self.GENTLE_SLEEP_TIME)
                time.sleep(self.GENTLE_SLEEP_TIME)
