import abc
import importlib
import logging
import typing

from django.conf import settings

from share.models.feature_flag import FeatureFlag
from share.models.index_backfill import IndexBackfill
from share.search.exceptions import IndexStrategyError
from share.search.index_status import IndexStatus
from share.search import messages
from share.util.checksum_iris import ChecksumIri


logger = logging.getLogger(__name__)


class IndexStrategy(abc.ABC):
    '''an abstraction for indexes in different places and ways.

    the IndexStrategy abstract-base-class has:
    * methods to observe and effect the lifecycles of a "search index"
      that is expected to evolve over time, aiming to ease migration
      and comparison across possible models and implementations
    * methods to get search results and feedback
    * abstract methods that must be implemented by each subclass
      (including on SpecificIndex, an abstract base class itself)

    each IndexStrategy subclass:
    * encapsulates all interaction with a particular type of search-engine cluster
    * may know of version- or cluster-specific features
      (should include identifiers like version numbers in subclass name)
    '''
    CURRENT_STRATEGY_CHECKSUM: ChecksumIri = None  # set on subclasses to protect against accidents

    __all_strategys_by_name = None  # cache for cls.all_strategies_by_name()

    @classmethod
    def clear_strategy_cache(self):
        self.__all_strategys_by_name = None

    @classmethod
    def all_strategies_by_name(cls) -> 'dict[str, IndexStrategy]':
        if cls.__all_strategys_by_name is None:
            cls.__all_strategys_by_name = {
                name: cls._load_from_settings(name, index_strategy_settings)
                for name, index_strategy_settings
                in settings.ELASTICSEARCH['INDEX_STRATEGIES'].items()
            }
        return cls.__all_strategys_by_name

    @classmethod
    def all_strategies(cls) -> 'typing.Iterable[IndexStrategy]':
        yield from cls.all_strategies_by_name().values()

    @classmethod
    def get_by_name(cls, index_strategy_name: str) -> 'IndexStrategy':
        try:
            return cls.all_strategies_by_name()[index_strategy_name]
        except KeyError:
            raise IndexStrategyError(f'unknown index strategy "{index_strategy_name}"')

    @classmethod
    def get_specific_index(cls, specific_indexname: str) -> 'IndexStrategy.SpecificIndex':
        for index_strategy in cls.all_strategies():
            try:
                return index_strategy.for_specific_index(specific_indexname)
            except IndexStrategyError:
                pass
        raise IndexStrategyError(f'unrecognized indexname "{specific_indexname}"')

    @classmethod
    def get_for_searching(cls, requested_name=None, *, with_default_fallback: bool = False) -> 'IndexStrategy.SpecificIndex':
        if requested_name is not None:
            try:  # could be a strategy name
                return cls.get_by_name(requested_name).pls_get_default_for_searching()
            except IndexStrategyError:
                try:  # could be a specific indexname
                    return cls.get_specific_index(requested_name)
                except IndexStrategyError:
                    raise IndexStrategyError(f'unknown name: "{requested_name}"')
        if with_default_fallback:
            return cls.get_for_searching(cls._default_strategyname_for_searching())
        raise ValueError('either provide non-None requested_name or with_default_fallback=True')

    @classmethod
    def _default_strategyname_for_searching(cls) -> str:
        return (
            'sharev2_elastic8'
            if FeatureFlag.objects.flag_is_up(FeatureFlag.ELASTIC_EIGHT_DEFAULT)
            else settings.DEFAULT_INDEX_STRATEGY_FOR_SEARCHING
        )

    @classmethod
    def _load_from_settings(cls, index_strategy_name, index_strategy_settings):
        assert set(index_strategy_settings) == {'INDEX_STRATEGY_CLASS', 'CLUSTER_SETTINGS'}, (
            'values in settings.ELASTICSEARCH[\'INDEX_STRATEGIES\'] must have keys: '
            'INDEX_STRATEGY_CLASS, CLUSTER_SETTINGS'
        )
        class_path = index_strategy_settings['INDEX_STRATEGY_CLASS']
        module_name, separator, class_name = class_path.rpartition('.')
        if not separator:
            raise IndexStrategyError(f'INDEX_STRATEGY_CLASS should be importable dotted-path to an IndexStrategy class; got "{class_path}"')
        assert module_name.startswith('share.search.index_strategy.'), (
            'for now, INDEX_STRATEGY_CLASS must start with "share.search.index_strategy."'
            f' (got "{module_name}")'
        )
        index_strategy_class = getattr(importlib.import_module(module_name), class_name)
        assert issubclass(index_strategy_class, cls)
        return index_strategy_class(
            name=index_strategy_name,
            cluster_settings=index_strategy_settings['CLUSTER_SETTINGS'],
        )

    def __init__(self, name, cluster_settings):
        self.name = name
        self.cluster_settings = cluster_settings

    def __repr__(self):
        return ''.join((
            self.__class__.__qualname__,
            f'(name={self.name})'
        ))

    @property
    def cluster_url(self):
        return self.cluster_settings['URL']

    @property
    def nonurgent_messagequeue_name(self):
        return f'{self.name}.nonurgent'

    @property
    def urgent_messagequeue_name(self):
        return f'{self.name}.urgent'

    @property
    def indexname_prefix(self):
        return f'{self.name}__'

    @property
    def indexname_wildcard(self):
        return f'{self.indexname_prefix}*'

    @property
    def current_indexname(self):
        return ''.join((
            self.indexname_prefix,
            self.CURRENT_STRATEGY_CHECKSUM.hexdigest,
        ))

    def assert_message_type(self, message_type: messages.MessageType):
        if message_type not in self.supported_message_types:
            raise IndexStrategyError(f'Invalid message_type "{message_type}" (expected {self.supported_message_types})')

    def assert_strategy_is_current(self):
        actual_checksum = self.compute_strategy_checksum()
        if actual_checksum != self.CURRENT_STRATEGY_CHECKSUM:
            raise IndexStrategyError(f'''
Unconfirmed changes in {self.__class__.__qualname__}!

If you made these changes on purpose, pls update {self.__class__.__qualname__} with:
```
    CURRENT_STRATEGY_CHECKSUM = {ChecksumIri.__name__}(
        checksumalgorithm_name='{actual_checksum.checksumalgorithm_name}',
        salt='{actual_checksum.salt}',
        hexdigest='{actual_checksum.hexdigest}',
    )
```''')

    def for_specific_index(self, specific_indexname) -> 'IndexStrategy.SpecificIndex':
        return self.SpecificIndex(self, specific_indexname)

    def for_current_index(self) -> 'IndexStrategy.SpecificIndex':
        return self.for_specific_index(self.current_indexname)

    def get_or_create_backfill(self):
        (index_backfill, _) = IndexBackfill.objects.get_or_create(index_strategy_name=self.name)
        return index_backfill

    def pls_start_backfill(self):
        self.get_or_create_backfill().pls_start(self)

    def pls_mark_backfill_complete(self):
        self.get_or_create_backfill().pls_mark_complete()

    @property
    @abc.abstractmethod
    def supported_message_types(self) -> typing.Iterable[messages.MessageType]:
        raise NotImplementedError

    @abc.abstractmethod
    def compute_strategy_checksum(self) -> ChecksumIri:
        '''get a dict (json-serializable and thereby checksummable) of all
        configuration held still by this IndexStrategy instance -- changes
        in this value's checksum may invoke changes in index lifecycle, as
        may be defined by IndexStrategy subclasses
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def each_specific_index(self) -> 'typing.Iterable[SpecificIndex]':
        raise NotImplementedError

    @abc.abstractmethod
    def pls_handle_messages_chunk(self, messages_chunk: messages.MessagesChunk) -> typing.Iterable[messages.IndexMessageResponse]:
        raise NotImplementedError

    @abc.abstractmethod
    def pls_make_default_for_searching(self, specific_index: 'SpecificIndex'):
        raise NotImplementedError

    @abc.abstractmethod
    def pls_get_default_for_searching(self) -> 'SpecificIndex':
        raise NotImplementedError

    # IndexStrategy.SpecificIndex must be implemented by subclasses
    # in their own `class SpecificIndex(IndexStrategy.SpecificIndex)`
    class SpecificIndex(abc.ABC):
        def __init__(self, index_strategy, indexname):
            if not indexname.startswith(index_strategy.indexname_prefix):
                raise IndexStrategyError(
                    f'invalid indexname "{indexname}"!'
                    f' (expected to start with "{index_strategy.indexname_prefix}")'
                )
            self.index_strategy = index_strategy
            self.indexname = indexname

        def __eq__(self, other):
            return (
                other.__class__ is self.__class__
                and other.index_strategy is self.index_strategy
                and other.indexname == self.indexname
            )

        def __repr__(self):
            return ''.join((
                self.__class__.__qualname__,
                f'(index_strategy={self.index_strategy}, '
                f'indexname={self.indexname})'
            ))

        @property
        def is_current(self):
            return self.indexname == self.index_strategy.current_indexname

        @abc.abstractmethod
        def pls_get_status(self) -> IndexStatus:
            raise NotImplementedError

        @abc.abstractmethod
        def pls_check_exists(self) -> bool:
            raise NotImplementedError

        @abc.abstractmethod
        def pls_create(self):
            raise NotImplementedError

        @abc.abstractmethod
        def pls_refresh(self):
            raise NotImplementedError

        @abc.abstractmethod
        def pls_delete(self):
            raise NotImplementedError

        @abc.abstractmethod
        def pls_start_keeping_live(self):
            raise NotImplementedError

        @abc.abstractmethod
        def pls_stop_keeping_live(self):
            raise NotImplementedError

        # @abc.abstractmethod
        # def pls_handle_query(self, **kwargs) -> TODO:  # (type consistent with search api model)
        #     raise NotImplementedError

        # optional for subclasses
        def pls_handle_query__sharev2_backcompat(self, request_body=None, request_queryparams=None) -> dict:
            raise NotImplementedError(f'{self.__class__.__name__} does not implement pls_handle_query__sharev2_backcompat (either implement it or don\'t use this strategy for backcompat)')
