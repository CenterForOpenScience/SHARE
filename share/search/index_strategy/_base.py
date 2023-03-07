import abc
import hashlib
import importlib
import json
import typing

from django.conf import settings
from django.utils.functional import cached_property

from share.search.exceptions import IndexStrategyError
from share.search import messages
from share import tasks


class IndexStrategy(abc.ABC):
    '''an abstraction for indexes in different places and ways.

    each IndexStrategy subclass:
    * may know of version- or cluster-specific features
      (should encapsulate its elasticsearch client library)
    * implements methods to observe and effect the lifecycle of a search index:
        * current_setup
        * pls_gather_status
        * pls_check_exists
        * pls_create
        * pls_open_for_searching
        * pls_handle_messages_chunk
        * pls_handle_query
        * pls_delete
    '''
    CURRENT_SETUP_CHECKSUM = None  # set on subclasses to protect against accidents

    __all_strategies = None  # private cache

    @classmethod
    def all_strategies(cls):
        if cls.__all_strategies is None:
            cls.__all_strategies = {
                index_strategy_name: cls._load_from_config(index_strategy_name)
                for index_strategy_name in settings.ELASTICSEARCH['INDEX_STRATEGIES'].keys()
            }
        return cls.__all_strategies

    @classmethod
    def by_name(cls, index_strategy_name: str):
        return cls.all_strategies()[index_strategy_name]

    @classmethod
    def by_request(cls, requested_index_strategy: str):
        index_strategy = cls.all_strategies().get(requested_index_strategy)
        if index_strategy is None:
            try:
                base_strategy_name = next(
                    strategy.name
                    for strategy in cls.all_strategies().values()
                    if requested_index_strategy.startswith(strategy.current_index_prefix)
                )
            except StopIteration:
                raise IndexStrategyError(f'unknown index-strategy "{requested_index_strategy}"')
            else:
                index_strategy = cls._load_from_config(base_strategy_name, requested_index_strategy)
        return index_strategy

    @classmethod
    def _load_from_config(cls, index_strategy_name, specific_index_name=None):
        # required known properties: INDEX_STRATEGY_CLASS, CLUSTER_URL
        index_config = settings.ELASTICSEARCH['INDEX_STRATEGIES'][index_strategy_name]
        module_name, class_name = index_config['INDEX_STRATEGY_CLASS'].split(':', maxsplit=1)
        assert module_name.startswith('share.search.index_strategy.')
        index_strategy_class = getattr(importlib.import_module(module_name), class_name)
        assert issubclass(index_strategy_class, IndexStrategy)
        return index_strategy_class(
            name=index_strategy_name,
            cluster_url=index_config['CLUSTER_URL'],
            cluster_auth=index_config.get('CLUSTER_AUTH', None),
            default_queue_name=index_config.get('DEFAULT_QUEUE', None),
            urgent_queue_name=index_config.get('URGENT_QUEUE', None),
            specific_index_name=specific_index_name,
        )

    def __init__(
        self, *,
        name,
        cluster_url,
        cluster_auth=None,
        default_queue_name=None,
        urgent_queue_name=None,
        specific_index_name=None,
    ):
        self.name = name
        self.cluster_url = cluster_url
        self.cluster_auth = cluster_auth
        self.default_queue_name = default_queue_name or name
        self.urgent_queue_name = urgent_queue_name or f'{self.default_queue_name}.urgent'
        if specific_index_name is not None:
            assert specific_index_name.startswith(self.current_index_prefix)
        self._specific_index_name = specific_index_name

    def get_queue_name(self, urgent: bool):
        return (
            self.urgent_queue_name
            if urgent
            else self.default_queue_name
        )

    def assert_message_type(self, message_type: messages.MessageType):
        if message_type not in self.supported_message_types:
            raise IndexStrategyError(f'Invalid message_type "{message_type}" (expected {self.supported_message_types})')

    @cached_property
    def current_setup_checksum(self):
        '''get a checksum (as iri) for all shared/static config in this setup

        (e.g. elastic settings, mappings)
        '''
        current_setup_str = json.dumps(
            self.current_setup(),
            sort_keys=True,
        )
        salt = self.__class__.__name__  # note: renaming an IndexStrategy subclass changes its checksum
        checksum_hex = (
            hashlib.sha256(
                f'{salt}{current_setup_str}'.encode(),
            )
            .hexdigest()
        )
        return f'urn:checksum:sha-256:{salt}:{checksum_hex}'

    @property
    def current_index_prefix(self):
        return f'{self.name}__'

    @property
    def current_index_wildcard(self):
        return f'{self.current_index_prefix}*'

    @property
    def current_index_name(self):
        checksum_hex = self.current_setup_checksum.rpartition(':')[-1]
        return f'{self.current_index_prefix}{checksum_hex}'

    @property
    def alias_for_searching(self):
        # the alias used for querying
        return f'{self.current_index_prefix}prime'

    def get_indexname_for_searching(self):
        return self._specific_index_name or self.alias_for_searching

    def get_indexname_for_updating(self):
        return self._specific_index_name or self.current_index_name

    def get_specific_indexname(self):
        return self._specific_index_name or self.current_index_name

    def assert_setup_is_current(self):
        setup_checksum = self.current_setup_checksum
        if setup_checksum != self.CURRENT_SETUP_CHECKSUM:
            raise IndexStrategyError(f'''
Unconfirmed changes in {self.__class__.__name__}!
Expected CURRENT_SETUP_CHECKSUM = '{self.CURRENT_SETUP_CHECKSUM}'
...but got '{setup_checksum}'
for the current setup:
{json.dumps(self.current_setup(), indent=4, sort_keys=True)}

If changing on purpose, update {self.__class__.__qualname__} with:
```
    CURRENT_SETUP_CHECKSUM = '{setup_checksum}'
```''')

    def pls_setup_as_needed(self):
        self.assert_setup_is_current()
        self.pls_create()
        self.pls_organize_backfill()

    def pls_organize_backfill(self):
        # TODO track/check backfill status somehow (if done, don't re-do)
        # using the non-urgent queue, schedule a task to schedule index tasks
        tasks.schedule_index_backfill.apply_async((self.name,))

    @abc.abstractmethod
    def current_setup(self):
        '''get a json-serializable representation of shared/static index config
        '''
        raise NotImplementedError(f'{self.__class__.__name__} must implement current_setup')

    @abc.abstractmethod
    def specific_index_statuses(self):
        raise NotImplementedError(f'{self.__class__.__name__} must implement specific_index_statuses')

    @abc.abstractmethod
    def pls_create(self):
        # check index exists (if not, create)
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_create')

    @abc.abstractmethod
    def pls_delete(self):
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_delete')

    @abc.abstractmethod
    def pls_open_for_searching(self):
        # check alias exists from name (if not, create)
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_open_for_searching')

    @property
    @abc.abstractmethod
    def supported_message_types(self) -> typing.Iterable[messages.MessageType]:
        raise NotImplementedError(f'{self.__class__.__name__} must implement supported_message_types')

    @abc.abstractmethod
    def pls_handle_messages_chunk(self, messages_chunk: messages.MessagesChunk) -> typing.Iterable[messages.IndexMessageResponse]:
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_handle_messages_chunk')

    @abc.abstractmethod
    def pls_check_exists(self):
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_check_exists')

    # TODO:
    # @abc.abstractmethod
    # def pls_handle_query(self, **kwargs):
    #     raise NotImplementedError(f'{self.__class__.__name__} must implement pls_handle_query')

    # optional for subclasses
    def pls_handle_query__api_backcompat(self, request_body, request_queryparams=None):
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_handle_query__api_backcompat')
