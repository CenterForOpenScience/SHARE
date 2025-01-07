from __future__ import annotations
import abc
import dataclasses
import functools
import logging
import typing

from share.search import messages
from share.models.index_backfill import IndexBackfill
from share.search.exceptions import IndexStrategyError
from share.search.index_status import IndexStatus
from share.util.checksum_iri import ChecksumIri
from trove.trovesearch.search_params import (
    CardsearchParams,
    ValuesearchParams,
)
from trove.trovesearch.search_handle import (
    CardsearchHandle,
    ValuesearchHandle,
)


logger = logging.getLogger(__name__)


_INDEXNAME_DELIM = '__'  # used to separate indexnames into a list of meaningful values


@dataclasses.dataclass
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

    name: str
    subname: str = ''  # if unspecified, uses current

    def __post_init__(self):
        if _INDEXNAME_DELIM in self.name:
            raise IndexStrategyError(f'strategy name may not contain "{_INDEXNAME_DELIM}" (got "{self.name}")')
        if not self.subname:
            self.subname = self.CURRENT_STRATEGY_CHECKSUM.hexdigest

    @property
    def nonurgent_messagequeue_name(self) -> str:
        return f'{self.name}.nonurgent'

    @property
    def urgent_messagequeue_name(self) -> str:
        return f'{self.name}.urgent'

    @property
    def indexname_prefix(self) -> str:
        # note: ends with _INDEXNAME_DELIM
        return _INDEXNAME_DELIM.join((self.name, self.subname, ''))

    @property
    def indexname_wildcard(self) -> str:
        return f'{self.indexname_prefix}*'

    @property
    def is_current(self) -> bool:
        return self.subname == self.CURRENT_STRATEGY_CHECKSUM.hexdigest

    @functools.cached_property
    def all_current_indexnames(self) -> tuple[str, ...]:
        self.assert_strategy_is_current()
        _single_indexname = ''.join((
            self.indexname_prefix,
            self.CURRENT_STRATEGY_CHECKSUM.hexdigest,
        ))
        return (_single_indexname,)

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

    def with_hex(self, subname: str):
        return dataclasses.replace(self, subname=subname)

    def get_index_by_shortname(self, shortname: str) -> typing.Self.SpecificIndex:
        return self.SpecificIndex(self, shortname)  # type: ignore[abstract]

    def for_current_index(self) -> IndexStrategy.SpecificIndex:
        return self.get_index_by_shortname(self.current_indexname)

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

    @property
    @abc.abstractmethod
    def backfill_message_type(self) -> messages.MessageType:
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
    def each_existing_index(self) -> typing.Iterator[SpecificIndex]:
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
    @dataclasses.dataclass
    class SpecificIndex(abc.ABC):
        index_strategy: IndexStrategy
        short_indexname: str  # unique per index_strategy

        def __post_init__(self):
            if self.short_indexname not in self.index_strategy.short_indexname_set:
                raise IndexStrategyError(
                    f'invalid short_indexname "{self.short_indexname}"!'
                    f' (expected to start with "{self.index_strategy.short_indexname_set}")'
                )

        @property
        def is_current(self) -> bool:
            return self.index_strategy.is_current

        @property
        def indexname(self) -> str:
            return f'{self.index_strategy.indexname_prefix}{self.short_indexname}'

        def pls_setup(self, *, skip_backfill=False):
            assert self.is_current, 'cannot setup a non-current index'
            _preexisting_index_count = sum(
                _index.pls_check_exists()
                for _index in self.index_strategy.each_existing_index()
            )
            self.pls_create()
            self.pls_start_keeping_live()
            if skip_backfill:
                _backfill = self.index_strategy.get_or_create_backfill()
                _backfill.backfill_status = _backfill.COMPLETE
                _backfill.save()
            if not _preexisting_index_count:  # first index for a strategy is automatic default
                self.index_strategy.pls_make_default_for_searching(self)

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

        # optional for subclasses
        def pls_handle_search__sharev2_backcompat(self, request_body=None, request_queryparams=None) -> dict:
            raise NotImplementedError(f'{self.__class__.__name__} does not implement pls_handle_search__sharev2_backcompat (either implement it or don\'t use this strategy for backcompat)')

        def pls_handle_cardsearch(self, cardsearch_params: CardsearchParams) -> CardsearchHandle:
            raise NotImplementedError

        def pls_handle_valuesearch(self, valuesearch_params: ValuesearchParams) -> ValuesearchHandle:
            raise NotImplementedError

        def pls_get_mappings(self) -> dict:
            raise NotImplementedError

        # TODO someday:
        # def pls_handle_propertysearch(self, propertysearch_params: PropertysearchParams) -> PropertysearchResponse:
        #     raise NotImplementedError
