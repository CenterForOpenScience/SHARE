from __future__ import annotations
import abc
import dataclasses
import functools
import logging
import typing

from share.search import messages
from share.models.index_backfill import IndexBackfill
from share.search.exceptions import IndexStrategyError
from share.search.index_status import (
    IndexStatus,
    StrategyStatus,
)
from share.util.checksum_iri import ChecksumIri
from trove.trovesearch.search_params import (
    CardsearchParams,
    ValuesearchParams,
)
from trove.trovesearch.search_handle import (
    CardsearchHandle,
    ValuesearchHandle,
)
from . import _indexnames as indexnames


logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
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
    CURRENT_STRATEGY_CHECKSUM: typing.ClassVar[ChecksumIri]  # set on subclasses to protect against accidents

    strategy_name: str
    strategy_check: str = ''  # if unspecified, uses current checksum

    def __post_init__(self):
        indexnames.raise_if_invalid_indexname_part(self.strategy_name)
        if not self.strategy_check:
            object.__setattr__(self, 'strategy_check', self.CURRENT_STRATEGY_CHECKSUM.hexdigest)
        indexnames.raise_if_invalid_indexname_part(self.strategy_check)

    @classmethod
    @functools.cache
    def index_subname_set(cls) -> frozenset[str]:
        return frozenset(cls.each_index_subname())

    def each_subnamed_index(self) -> typing.Iterator[SpecificIndex]:
        for _subname in self.index_subname_set():
            yield self.get_index(_subname)

    @property
    def nonurgent_messagequeue_name(self) -> str:
        return f'{self.strategy_name}.nonurgent'

    @property
    def urgent_messagequeue_name(self) -> str:
        return f'{self.strategy_name}.urgent'

    @property
    def indexname_prefix_parts(self) -> list[str]:
        return [self.strategy_name, self.strategy_check]

    @property
    def indexname_prefix(self) -> str:
        return indexnames.combine_indexname_parts(*self.indexname_prefix_parts)

    @property
    def indexname_wildcard(self) -> str:
        return f'{self.indexname_prefix}*'

    @property
    def is_current(self) -> bool:
        return self.strategy_check == self.CURRENT_STRATEGY_CHECKSUM.hexdigest

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

    def get_index(self, subname: str) -> SpecificIndex:
        return self.SpecificIndex(self, subname)  # type: ignore[abstract]

    def parse_full_index_name(self, index_name: str) -> SpecificIndex:
        _parts = indexnames.parse_indexname_parts(index_name)
        try:
            (_strategy_name, _strategy_check, *_etc) = _parts
        except ValueError:
            raise IndexStrategyError(f'expected "strategyname__strategycheck", at least (got "{index_name}")')
        if _strategy_name != self.strategy_name:
            raise IndexStrategyError(f'this index belongs to another strategy (expected strategy name "{self.strategy_name}"; got "{_strategy_name}" from index name {index_name})')
        _strategy = self.with_strategy_check(_strategy_check)
        return _strategy.get_index(_etc[0] if _etc else '')

    def with_strategy_check(self, strategy_check: str) -> typing.Self:
        return dataclasses.replace(self, strategy_check=strategy_check)

    def pls_setup(self, *, skip_backfill=False) -> None:
        if not self.is_current:
            raise IndexStrategyError('cannot setup a non-current strategy')
        for _index in self.each_subnamed_index():
            _index.pls_create()
            _index.pls_start_keeping_live()
        if skip_backfill:
            _backfill = self.get_or_create_backfill()
            _backfill.backfill_status = _backfill.COMPLETE
            _backfill.save()

    def pls_teardown(self) -> None:
        for _index in self.each_existing_index():
            _index.pls_delete()

    def get_or_create_backfill(self):
        (index_backfill, _) = IndexBackfill.objects.get_or_create(
            index_strategy_name=self.strategy_name,
        )
        return index_backfill

    def pls_start_backfill(self):
        self.get_or_create_backfill().pls_start(self)

    def pls_mark_backfill_complete(self):
        self.get_or_create_backfill().pls_mark_complete()
        self.pls_refresh()  # explicit refresh after backfill

    def pls_check_exists(self) -> bool:
        return all(
            _index.pls_check_exists()
            for _index in self.each_subnamed_index()
        )

    def pls_refresh(self) -> None:
        for _index in self.each_subnamed_index():
            _index.pls_refresh()

    def pls_start_keeping_live(self):
        for _index in self.each_subnamed_index():
            _index.pls_start_keeping_live()

    def pls_stop_keeping_live(self):
        for _index in self.each_live_index():
            _index.pls_stop_keeping_live()

    def pls_get_strategy_status(self) -> StrategyStatus:
        _index_statuses: list[IndexStatus] = []
        _prior_strategy_statuses: list[StrategyStatus] = []
        if self.is_current:
            _index_statuses = [
                _index.pls_get_status()
                for _index in self.each_subnamed_index()
            ]
            _prior_strategies = {
                _index.index_strategy
                for _index in self.each_existing_index(any_strategy_check=True)
                if not _index.index_strategy.is_current
            }
            _prior_strategy_statuses = [
                _strategy.pls_get_strategy_status()
                for _strategy in _prior_strategies
            ]
        else:
            _index_statuses = [
                _index.pls_get_status()
                for _index in self.each_existing_index()
            ]
        return StrategyStatus(
            strategy_name=self.strategy_name,
            strategy_check=self.strategy_check,
            is_set_up=self.pls_check_exists(),
            is_default_for_searching=(self == self.pls_get_default_for_searching()),
            index_statuses=_index_statuses,
            existing_prior_strategies=_prior_strategy_statuses,
        )

    ###
    # abstract methods (required for concrete subclasses)

    @classmethod
    @abc.abstractmethod
    def compute_strategy_checksum(self) -> ChecksumIri:
        '''get a dict (json-serializable and thereby checksummable) of all
        configuration held still by this IndexStrategy subclass -- changes
        in the checksum may result in new indices being created and filled
        '''
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def each_index_subname(self) -> typing.Iterable[str]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def supported_message_types(self) -> typing.Iterable[messages.MessageType]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def backfill_message_type(self) -> messages.MessageType:
        raise NotImplementedError

    @abc.abstractmethod
    def each_existing_index(self, *, any_strategy_check: bool = False) -> typing.Iterator[SpecificIndex]:
        raise NotImplementedError

    @abc.abstractmethod
    def each_live_index(self, *, any_strategy_check: bool = False) -> typing.Iterator[SpecificIndex]:
        raise NotImplementedError

    @abc.abstractmethod
    def pls_handle_messages_chunk(self, messages_chunk: messages.MessagesChunk) -> typing.Iterable[messages.IndexMessageResponse]:
        raise NotImplementedError

    @abc.abstractmethod
    def pls_make_default_for_searching(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def pls_get_default_for_searching(self) -> IndexStrategy:
        raise NotImplementedError

    ###
    # optional implementations

    def pls_handle_cardsearch(self, cardsearch_params: CardsearchParams) -> CardsearchHandle:
        raise NotImplementedError

    def pls_handle_valuesearch(self, valuesearch_params: ValuesearchParams) -> ValuesearchHandle:
        raise NotImplementedError

    def pls_handle_search__passthru(self, request_body=None, request_queryparams=None) -> dict:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement pls_handle_search__passthru (either implement it or don\'t use this strategy for that)')

    # IndexStrategy.SpecificIndex must be implemented by subclasses
    # in their own `class SpecificIndex(IndexStrategy.SpecificIndex)`
    @dataclasses.dataclass
    class SpecificIndex(abc.ABC):
        index_strategy: IndexStrategy
        subname: str  # unique per index_strategy

        @property
        def is_current(self) -> bool:
            return self.index_strategy.is_current

        @property
        def has_valid_subname(self) -> bool:
            return self.subname in self.index_strategy.index_subname_set()

        @property
        def full_index_name(self) -> str:
            return indexnames.combine_indexname_parts(
                *self.index_strategy.indexname_prefix_parts,
                self.subname,
            )

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

        def pls_get_mappings(self) -> dict:
            raise NotImplementedError

        # TODO someday:
        # def pls_handle_propertysearch(self, propertysearch_params: PropertysearchParams) -> PropertysearchResponse:
        #     raise NotImplementedError
