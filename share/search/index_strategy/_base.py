import abc
import hashlib
import importlib
import json
import typing

from django.conf import settings
from django.db import transaction
from django.utils.functional import cached_property

from share.models.index_backfill import IndexBackfill
from share.search.exceptions import IndexStrategyError
from share.search.index_status import IndexStatus
from share.search import messages


class IndexStrategy(abc.ABC):
    '''an abstraction for indexes in different places and ways.

    each IndexStrategy subclass:
    * may know of version- or cluster-specific features
      (should encapsulate its elasticsearch client library)
    * implements abstract methods to observe and effect the lifecycle of an index
    '''
    CURRENT_SETUP_CHECKSUM = None  # set on subclasses to protect against accidents
    SUPPORTS_BACKFILL = True  # set False on subclasses that don't support backfill

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
    def by_strategy_name(cls, index_strategy_name: str):
        try:
            return cls.all_strategies()[index_strategy_name]
        except KeyError:
            raise IndexStrategyError(f'unknown index strategy "{index_strategy_name}"')

    @classmethod
    def by_specific_indexname(cls, specific_indexname: str):
        # check for match against each strategy's indexname_prefix
        try:
            index_strategy_name = next(
                strategy.name
                for strategy in cls.all_strategies().values()
                if specific_indexname.startswith(strategy.indexname_prefix)
            )
        except StopIteration:
            raise IndexStrategyError(f'unrecognized index "{specific_indexname}"')
        return cls._load_from_config(index_strategy_name, specific_indexname)

    @classmethod
    def by_request(cls, requested_strategy=None, *, request=None, default_strategy=None):
        if requested_strategy is None:
            assert request is not None
            requested_strategy = request.GET.get('indexStrategy')
        # requested_strategy could be a strategy name or a specific index name
        try:
            return cls.by_strategy_name(requested_strategy)
        except IndexStrategyError:
            try:
                return cls.by_specific_indexname(requested_strategy)
            except IndexStrategyError:
                if default_strategy is not None:
                    return cls.by_request(default_strategy)
                raise IndexStrategyError(f'bad strategy request: "{requested_strategy}"')

    @classmethod
    def _load_from_config(cls, index_strategy_name, specific_indexname=None):
        index_config = settings.ELASTICSEARCH['INDEX_STRATEGIES'][index_strategy_name]
        assert set(index_config) == {'INDEX_STRATEGY_CLASS', 'CLUSTER_SETTINGS'}, (
            'values in settings.ELASTICSEARCH[\'INDEX_STRATEGIES\'] must have keys: '
            'INDEX_STRATEGY_CLASS, CLUSTER_SETTINGS'
        )
        module_name, class_name = index_config['INDEX_STRATEGY_CLASS'].split(':', maxsplit=1)
        assert module_name.startswith('share.search.index_strategy.')
        index_strategy_class = getattr(importlib.import_module(module_name), class_name)
        assert issubclass(index_strategy_class, IndexStrategy)
        return index_strategy_class(
            name=index_strategy_name,
            cluster_settings=index_config['CLUSTER_SETTINGS'],
            specific_indexname=specific_indexname,
        )

    def __init__(
        self, *,
        name,
        cluster_settings,
        specific_indexname=None,
    ):
        self.name = name
        self.cluster_settings = cluster_settings
        if specific_indexname is not None:
            assert specific_indexname.startswith(self.indexname_prefix)
        self._specific_indexname = specific_indexname

    def get_queue_name(self, urgent: bool):
        return (
            self.urgent_queue_name
            if urgent
            else self.nonurgent_queue_name
        )

    @property
    def nonurgent_queue_name(self):
        return self.name

    @property
    def urgent_queue_name(self):
        return f'{self.nonurgent_queue_name}.urgent'

    def assert_message_type(self, message_type: messages.MessageType):
        if message_type not in self.supported_message_types:
            raise IndexStrategyError(f'Invalid message_type "{message_type}" (expected {self.supported_message_types})')

    @property
    def cluster_url(self):
        return self.cluster_settings['URL']

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
    def indexname_prefix(self):
        return f'{self.name}__'

    @property
    def indexname_wildcard(self):
        return f'{self.indexname_prefix}*'

    @property
    def _current_indexname(self):
        checksum_hex = self.current_setup_checksum.rpartition(':')[-1]
        return f'{self.indexname_prefix}{checksum_hex}'

    @property
    def indexname(self):
        return self._specific_indexname or self._current_indexname

    @property
    def is_current(self):
        return self.indexname == self._current_indexname

    def assert_setup_is_current(self):
        setup_checksum = self.current_setup_checksum
        if setup_checksum != self.CURRENT_SETUP_CHECKSUM:
            raise IndexStrategyError(f'''
Unconfirmed changes in {self.__class__.__name__}!
Expected CURRENT_SETUP_CHECKSUM = '{self.CURRENT_SETUP_CHECKSUM}'
...but got '{setup_checksum}'

If changes were made on purpose, update {self.__class__.__qualname__} with:
```
    CURRENT_SETUP_CHECKSUM = '{setup_checksum}'
```''')

    def pls_setup_as_needed(self, *, start_backfill=False):
        self.assert_setup_is_current()
        self.pls_create()
        if start_backfill:
            self.pls_start_backfill()

    def pls_start_backfill(self):
        with transaction.atomic():
            (index_backfill, created) = IndexBackfill.objects.get_or_create(
                index_strategy_name=self.name,
                defaults={'specific_indexname': self.indexname},
            )
            if index_backfill.backfill_status != IndexBackfill.INITIAL:
                raise IndexStrategyError(
                    f'backfill status must be "{IndexBackfill.INITIAL}"; got {index_backfill}'
                )
            index_backfill.backfill_status = IndexBackfill.WAITING
            index_backfill.specific_indexname = self.indexname
            index_backfill.save()
        import share.tasks
        share.tasks.schedule_index_backfill.apply_async((index_backfill.id,))

    def pls_mark_backfill_complete(self):
        with transaction.atomic():
            index_backfill = IndexBackfill.objects.get(index_strategy_name=self.name)
            assert index_backfill.backfill_status == IndexBackfill.INDEXING
            index_backfill.specific_indexname = self.indexname
            index_backfill.backfill_status = IndexBackfill.COMPLETE
            index_backfill.save()

    @abc.abstractmethod
    def current_setup(self):
        '''get a json-serializable representation of shared/static index config
        '''
        raise NotImplementedError(f'{self.__class__.__name__} must implement current_setup')

    @abc.abstractmethod
    def specific_index_statuses(self) -> typing.Iterable[IndexStatus]:
        raise NotImplementedError(f'{self.__class__.__name__} must implement specific_index_statuses')

    @abc.abstractmethod
    def get_indexname_for_searching(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def get_indexnames_for_keeping_live(self, message_type: messages.MessageType) -> typing.Iterable[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def pls_check_exists(self):
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_check_exists')

    @abc.abstractmethod
    def pls_create(self):
        # check index exists (if not, create)
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_create')

    @abc.abstractmethod
    def pls_delete(self):
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_delete')

    @abc.abstractmethod
    def pls_make_default_for_searching(self):
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_make_default_for_searching')

    @property
    @abc.abstractmethod
    def supported_message_types(self) -> typing.Iterable[messages.MessageType]:
        raise NotImplementedError(f'{self.__class__.__name__} must implement supported_message_types')

    @abc.abstractmethod
    def pls_handle_messages_chunk(self, messages_chunk: messages.MessagesChunk) -> typing.Iterable[messages.IndexMessageResponse]:
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_handle_messages_chunk')

    # TODO:
    # @abc.abstractmethod
    # def pls_handle_query(self, **kwargs):
    #     raise NotImplementedError(f'{self.__class__.__name__} must implement pls_handle_query')

    # optional for subclasses
    def pls_handle_query__api_backcompat(self, request_body, request_queryparams=None):
        raise NotImplementedError(f'{self.__class__.__name__} must implement pls_handle_query__api_backcompat')
