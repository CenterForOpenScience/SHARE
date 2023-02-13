import abc
import importlib
import typing

from django.conf import settings

from share.search.exceptions import IndexSetupError
from share.search import messages


class IndexSetup(abc.ABC):
    @classmethod
    def all_indexes(cls):
        return tuple(
            cls._load_from_config(index_name, index_config)
            for index_name, index_config in settings.ELASTICSEARCH['INDEXES'].items()
        )

    @classmethod
    def by_name(cls, index_name):
        index_config = settings.ELASTICSEARCH['INDEXES'][index_name]
        return cls._load_from_config(index_name, index_config)

    @classmethod
    def _load_from_config(cls, index_name, index_config):
        # required known properties: INDEX_SETUP, CLUSTER_URL
        module_name, class_name = index_config['INDEX_SETUP'].split(':', maxsplit=1)
        assert module_name.startswith('share.search.')
        index_setup_class = getattr(importlib.import_module(module_name), class_name)
        assert issubclass(index_setup_class, IndexSetup)
        return index_setup_class(
            index_name=index_name,
            cluster_url=index_config['CLUSTER_URL'],
            default_queue_name=index_config.get('DEFAULT_QUEUE', None),
            urgent_queue_name=index_config.get('URGENT_QUEUE', None),
        )

    def __init__(self, index_name, cluster_url, default_queue_name=None, urgent_queue_name=None):
        self.index_name = index_name
        self.cluster_url = cluster_url
        self.default_queue_name = default_queue_name or index_name
        self.urgent_queue_name = urgent_queue_name or f'{self.default_queue_name}.urgent'

    def assert_message_type(self, message_type: messages.MessageType):
        if message_type not in self.supported_message_types:
            raise IndexSetupError(f'Invalid message_type "{message_type}" (expected {self.supported_message_types})')

    @property
    @abc.abstractmethod
    def supported_message_types(self) -> typing.Iterable[messages.MessageType]:
        raise NotImplementedError

    @abc.abstractmethod
    def pls_handle_messages(self, message_type: messages.MessageType, messages_chunk: typing.Iterable[messages.DaemonMessage]) -> typing.Iterable[messages.HandledMessageResponse]:
        raise NotImplementedError

    @abc.abstractmethod
    def exists_as_expected(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def pls_setup_as_needed(self):
        raise NotImplementedError

    @abc.abstractmethod
    def pls_create(self):
        raise NotImplementedError

    @abc.abstractmethod
    def pls_delete(self):
        raise NotImplementedError

    @abc.abstractmethod
    def pls_organize_redo(self):
        raise NotImplementedError
