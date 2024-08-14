import abc
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
from trove.trovesearch.search_response import (
    CardsearchResponse,
    ValuesearchResponse,
)


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
    CURRENT_STRATEGY_CHECKSUM: ChecksumIri  # set on subclasses to protect against accidents

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return ''.join((
            self.__class__.__qualname__,
            f'(name="{self.name}")'
        ))

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
        return self.SpecificIndex(self, specific_indexname)  # type: ignore[abstract]

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

        def pls_setup(self, *, skip_backfill=False):
            assert self.is_current, 'cannot setup a non-current index'
            _preexisting_index_count = sum(
                _index.pls_check_exists()
                for _index in self.index_strategy.each_specific_index()
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

        def pls_handle_cardsearch(self, cardsearch_params: CardsearchParams) -> CardsearchResponse:
            raise NotImplementedError

        def pls_handle_valuesearch(self, valuesearch_params: ValuesearchParams) -> ValuesearchResponse:
            raise NotImplementedError

        def pls_get_mappings(self) -> dict:
            raise NotImplementedError

        # TODO someday:
        # def pls_handle_propertysearch(self, propertysearch_params: PropertysearchParams) -> PropertysearchResponse:
        #     raise NotImplementedError
