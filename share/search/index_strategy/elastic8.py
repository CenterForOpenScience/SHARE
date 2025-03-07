from __future__ import annotations
import abc
import collections
from collections.abc import Mapping
import dataclasses
import functools
from http import HTTPStatus
import logging
import types
import typing

from django.conf import settings
import elasticsearch8
from elasticsearch8.helpers import streaming_bulk

from share.search.index_strategy._base import IndexStrategy
from share.search.index_status import IndexStatus
from share.search import messages
from share.search.index_strategy._util import timestamp_to_readable_datetime
from share.util.checksum_iri import ChecksumIri
from ._indexnames import (
    parse_indexname_parts,
    combine_indexname_parts,
)


logger = logging.getLogger(__name__)


class Elastic8IndexStrategy(IndexStrategy):
    '''abstract base class for index strategies using elasticsearch 8
    '''
    index_definitions: typing.ClassVar[dict[str, IndexDefinition]]

    ###
    # for use when defining abstract methods in subclasses

    @dataclasses.dataclass(frozen=True)
    class IndexDefinition:
        mappings: dict
        settings: dict

    @dataclasses.dataclass
    class MessageActionSet:
        message_target_id: int
        actions_by_subname: dict[str, typing.Iterable[dict]]

    ###
    # abstract methods for subclasses to implement

    @classmethod
    @abc.abstractmethod
    def define_current_indexes(cls) -> dict[str, IndexDefinition]:
        raise NotImplementedError

    @abc.abstractmethod
    def build_elastic_actions(
        self,
        messages_chunk: messages.MessagesChunk,
    ) -> typing.Iterable[MessageActionSet]:
        raise NotImplementedError

    def after_chunk(
        self,
        messages_chunk: messages.MessagesChunk,
        affected_indexnames: typing.Iterable[str],
    ) -> None:
        ...  # implement when needed

    ###
    # helper methods for subclasses to use (or override)

    def build_index_action(self, doc_id, doc_source):
        return {
            '_op_type': 'index',
            '_id': str(doc_id),
            '_source': doc_source,
        }

    def build_delete_action(self, doc_id):
        return {
            '_op_type': 'delete',
            '_id': str(doc_id),
        }

    def build_update_action(self, doc_id, doc_source):
        return {
            '_op_type': 'update',
            '_id': str(doc_id),
            'doc': doc_source,
        }

    ###
    # implementation for subclasses to ignore

    # abstract method from IndexStrategy
    @classmethod
    def compute_strategy_checksum(cls):
        _current_json = {
            _subname: dataclasses.asdict(_def)
            for _subname, _def in cls.current_index_defs().items()
        }
        if set(_current_json.keys()) == {''}:
            _current_json = _current_json['']
        return ChecksumIri.digest_json(
            checksumalgorithm_name='sha-256',
            salt=cls.__name__,
            raw_json=_current_json,
        )

    # abstract method from IndexStrategy
    @classmethod
    def each_index_subname(self) -> typing.Iterable[str]:
        yield from self.current_index_defs().keys()

    @classmethod
    @functools.cache
    def current_index_defs(cls) -> Mapping[str, IndexDefinition]:
        # readonly and cached per class
        return types.MappingProxyType(cls.define_current_indexes())

    @classmethod
    @functools.cache
    def _get_elastic8_client(cls) -> elasticsearch8.Elasticsearch:
        should_sniff = settings.ELASTICSEARCH['SNIFF']
        timeout = settings.ELASTICSEARCH['TIMEOUT']
        return elasticsearch8.Elasticsearch(
            settings.ELASTICSEARCH8_URL,
            # security:
            ca_certs=settings.ELASTICSEARCH8_CERT_PATH,
            basic_auth=(
                (settings.ELASTICSEARCH8_USERNAME, settings.ELASTICSEARCH8_SECRET)
                if settings.ELASTICSEARCH8_SECRET is not None
                else None
            ),
            # retry:
            retry_on_timeout=True,
            request_timeout=timeout,
            # sniffing:
            sniff_on_start=should_sniff,
            sniff_before_requests=should_sniff,
            sniff_on_node_failure=should_sniff,
            sniff_timeout=timeout,
            min_delay_between_sniffing=timeout,
        )

    @property
    def es8_client(self):
        return self._get_elastic8_client()  # cached classmethod for shared client

    # abstract method from IndexStrategy
    def each_existing_index(self, *, any_strategy_check: bool = False):
        _index_wildcard = (
            combine_indexname_parts(self.strategy_name, '*')
            if any_strategy_check
            else self.indexname_wildcard
        )
        indexname_set = set(
            self.es8_client.indices
            .get(index=_index_wildcard, features=',')
            .keys()
        )
        for indexname in indexname_set:
            _index = self.parse_full_index_name(indexname)
            assert _index.index_strategy.strategy_name == self.strategy_name
            yield _index

    def each_live_index(self, *, any_strategy_check: bool = False):
        for _indexname in self._get_indexnames_for_alias(self._alias_for_keeping_live):
            _index = self.parse_full_index_name(_indexname)
            if any_strategy_check or (_index.index_strategy == self):
                yield _index

    # abstract method from IndexStrategy
    def pls_handle_messages_chunk(self, messages_chunk):
        self.assert_message_type(messages_chunk.message_type)
        _action_tracker = _ActionTracker()
        _bulk_stream = streaming_bulk(
            self.es8_client,
            self._elastic_actions_with_index(messages_chunk, _action_tracker),
            raise_on_error=False,
            max_retries=settings.ELASTICSEARCH['MAX_RETRIES'],
        )
        _affected_indexnames: set[str] = set()
        for (_ok, _response) in _bulk_stream:
            (_op_type, _response_body) = next(iter(_response.items()))
            _status = _response_body.get('status')
            _docid = _response_body['_id']
            _indexname = _response_body['_index']
            _affected_indexnames.add(_indexname)
            _is_done = _ok or (_op_type == 'delete' and _status == 404)
            if _is_done:
                _finished_message_id = _action_tracker.action_done(_indexname, _docid)
                if _finished_message_id is not None:
                    yield messages.IndexMessageResponse(
                        is_done=True,
                        index_message=messages.IndexMessage(messages_chunk.message_type, _finished_message_id),
                        status_code=HTTPStatus.OK.value,
                        error_text=None,
                    )
                    _action_tracker.forget_message(_finished_message_id)
            else:
                _action_tracker.action_errored(_indexname, _docid)
                yield messages.IndexMessageResponse(
                    is_done=False,
                    index_message=messages.IndexMessage(
                        messages_chunk.message_type,
                        _action_tracker.get_message_id(_docid),
                    ),
                    status_code=_status,
                    error_text=str(_response_body),
                )
        for _message_id in _action_tracker.remaining_done_messages():
            yield messages.IndexMessageResponse(
                is_done=True,
                index_message=messages.IndexMessage(messages_chunk.message_type, _message_id),
                status_code=HTTPStatus.OK.value,
                error_text=None,
            )
        self.after_chunk(messages_chunk, _affected_indexnames)

    # abstract method from IndexStrategy
    def pls_make_default_for_searching(self):
        self._set_indexnames_for_alias(
            self._alias_for_searching,
            {self.indexname_wildcard},
        )

    # abstract method from IndexStrategy
    def pls_get_default_for_searching(self) -> IndexStrategy:
        _searchnames = self._get_indexnames_for_alias(self._alias_for_searching)
        try:
            (_indexname, *_) = _searchnames
        except ValueError:
            return self  # no default set, this one's fine
        (_strategyname, _strategycheck, *_) = parse_indexname_parts(_indexname)
        assert _strategyname == self.strategy_name
        _strategycheck = _strategycheck.rstrip('*')  # may be a wildcard alias
        return self.with_strategy_check(_strategycheck)

    # abstract method from IndexStrategy
    def pls_handle_search__passthru(self, request_body=None, request_queryparams=None) -> dict:
        _queryparams = request_queryparams or {}
        _requested_strategy = _queryparams.pop('indexStrategy', '')
        _indexname = self.indexname_wildcard
        if _requested_strategy and _requested_strategy.startswith(self.indexname_prefix):
            _index = self.parse_full_index_name(_requested_strategy)
            if _index.has_valid_subname:
                _indexname = _index.full_index_name
        return self.es8_client.search(
            index=_indexname,
            body={
                **(request_body or {}),
                'track_total_hits': True,
            },
            params=(request_queryparams or {}),
        )

    # override from IndexStrategy
    def pls_refresh(self):
        super().pls_refresh()  # refreshes each index
        logger.debug('%s: Waiting for yellow status', self.strategy_name)
        self.es8_client.cluster.health(wait_for_status='yellow')

    @property
    def _alias_for_searching(self):
        return combine_indexname_parts(self.strategy_name, 'search')

    @property
    def _alias_for_keeping_live(self):
        return combine_indexname_parts(self.strategy_name, 'live')

    def _elastic_actions_with_index(
        self,
        messages_chunk: messages.MessagesChunk,
        action_tracker: _ActionTracker,
    ):
        for _actionset in self.build_elastic_actions(messages_chunk):
            for _index_subname, _elastic_actions in _actionset.actions_by_subname.items():
                _indexnames = self._get_indexnames_for_action(
                    index_subname=_index_subname,
                    is_backfill_action=messages_chunk.message_type.is_backfill,
                )
                for _elastic_action in _elastic_actions:
                    _docid = _elastic_action['_id']
                    for _indexname in _indexnames:
                        action_tracker.add_action(_actionset.message_target_id, _indexname, _docid)
                        _elastic_action_with_index = {
                            **_elastic_action,
                            '_index': _indexname,
                        }
                        logger.debug('%s: elastic action: %r', self, _elastic_action_with_index)
                        yield _elastic_action_with_index
            action_tracker.done_scheduling(_actionset.message_target_id)

    def _get_indexnames_for_action(
        self,
        index_subname: str,
        *,
        is_backfill_action: bool = False,
    ) -> set[str]:
        if is_backfill_action:
            return {self.get_index(index_subname).full_index_name}
        return {
            _index.full_index_name
            for _index in self.each_live_index()
            if _index.subname == index_subname
        }

    def _get_indexnames_for_alias(self, alias_name) -> set[str]:
        try:
            aliases = self.es8_client.indices.get_alias(name=alias_name)
            return set(aliases.keys())
        except elasticsearch8.exceptions.NotFoundError:
            return set()

    def _add_indexname_to_alias(self, alias_name, indexname):
        self.es8_client.indices.update_aliases(actions=[
            {'add': {'index': indexname, 'alias': alias_name}},
        ])

    def _remove_indexname_from_alias(self, alias_name, indexname):
        self.es8_client.indices.update_aliases(actions=[
            {'remove': {'index': indexname, 'alias': alias_name}},
        ])

    def _set_indexnames_for_alias(self, alias_name, indexnames):
        already_aliased = self._get_indexnames_for_alias(alias_name)
        want_aliased = set(indexnames)
        if already_aliased == want_aliased:
            logger.info(f'alias "{alias_name}" already correct ({want_aliased}), doing nothing')
        else:
            to_remove = tuple(already_aliased - want_aliased)
            to_add = tuple(want_aliased - already_aliased)
            logger.warning(f'alias "{alias_name}": removing indexes {to_remove} and adding indexes {to_add}')
            self.es8_client.indices.update_aliases(actions=[
                *(
                    {'remove': {'index': indexname, 'alias': alias_name}}
                    for indexname in to_remove
                ),
                *(
                    {'add': {'index': indexname, 'alias': alias_name}}
                    for indexname in to_add
                ),
            ])

    @dataclasses.dataclass
    class SpecificIndex(IndexStrategy.SpecificIndex):
        index_strategy: Elastic8IndexStrategy  # note: narrower type

        @property
        def index_def(self) -> Elastic8IndexStrategy.IndexDefinition:
            return self.index_strategy.current_index_defs()[self.subname]

        # abstract method from IndexStrategy.SpecificIndex
        def pls_get_status(self) -> IndexStatus:
            if not self.pls_check_exists():
                return IndexStatus(
                    index_subname=self.subname,
                    specific_indexname=self.full_index_name,
                    is_kept_live=False,
                    is_default_for_searching=False,
                    doc_count=0,
                    creation_date='',
                )
            index_info = (
                self.index_strategy.es8_client.indices
                .get(index=self.full_index_name, features='aliases,settings')
                [self.full_index_name]
            )
            index_aliases = set(index_info['aliases'].keys())
            creation_date = timestamp_to_readable_datetime(
                index_info['settings']['index']['creation_date']
            )
            doc_count = (
                self.index_strategy.es8_client.indices
                .stats(index=self.full_index_name, metric='docs')
                ['indices'][self.full_index_name]['primaries']['docs']['count']
            )
            return IndexStatus(
                index_subname=self.subname,
                specific_indexname=self.full_index_name,
                is_kept_live=(
                    self.index_strategy._alias_for_keeping_live
                    in index_aliases
                ),
                is_default_for_searching=(
                    self.index_strategy._alias_for_searching
                    in index_aliases
                ),
                creation_date=creation_date,
                doc_count=doc_count,
            )

        # abstract method from IndexStrategy.SpecificIndex
        def pls_check_exists(self):
            _indexname = self.full_index_name
            _result = bool(
                self.index_strategy.es8_client.indices
                .exists(index=_indexname)
            )
            logger.info(
                f'{_indexname}: exists'
                if _result
                else f'{_indexname}: does not exist'
            )
            return _result

        # abstract method from IndexStrategy.SpecificIndex
        def pls_create(self):
            assert self.is_current, (
                'cannot create a non-current version of an index!'
            )
            index_to_create = self.full_index_name
            logger.debug('Ensuring index %s', index_to_create)
            index_exists = (
                self.index_strategy.es8_client.indices
                .exists(index=index_to_create)
            )
            if not index_exists:
                logger.info('Creating index %s', index_to_create)
                _index_def = self.index_def
                (
                    self.index_strategy.es8_client.indices
                    .create(
                        index=index_to_create,
                        settings=_index_def.settings,
                        mappings=_index_def.mappings,
                    )
                )
                self.pls_refresh()

        # abstract method from IndexStrategy.SpecificIndex
        def pls_refresh(self):
            _indexname = self.full_index_name
            (
                self.index_strategy.es8_client.indices
                .refresh(index=_indexname)
            )
            logger.info('%s: Refreshed', _indexname)

        # abstract method from IndexStrategy.SpecificIndex
        def pls_delete(self):
            _indexname = self.full_index_name
            (
                self.index_strategy.es8_client.indices
                .delete(index=_indexname, ignore=[400, 404])
            )
            logger.warning('%s: deleted', _indexname)

        # abstract method from IndexStrategy.SpecificIndex
        def pls_start_keeping_live(self):
            self.index_strategy._add_indexname_to_alias(
                indexname=self.full_index_name,
                alias_name=self.index_strategy._alias_for_keeping_live,
            )
            logger.info('%r: now kept live', self)

        # abstract method from IndexStrategy.SpecificIndex
        def pls_stop_keeping_live(self):
            self.index_strategy._remove_indexname_from_alias(
                indexname=self.full_index_name,
                alias_name=self.index_strategy._alias_for_keeping_live,
            )
            logger.warning('%r: no longer kept live', self)

        def pls_get_mappings(self):
            return self.index_strategy.es8_client.indices.get_mapping(index=self.full_index_name).body


@dataclasses.dataclass
class _ActionTracker:
    messageid_by_docid: dict[str, int] = dataclasses.field(default_factory=dict)
    actions_by_messageid: dict[int, set[tuple[str, str]]] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(set),
    )
    errored_messageids: set[int] = dataclasses.field(default_factory=set)
    fully_scheduled_messageids: set[int] = dataclasses.field(default_factory=set)

    def add_action(self, message_id: int, index_name: str, doc_id: str):
        self.messageid_by_docid[doc_id] = message_id
        self.actions_by_messageid[message_id].add((index_name, doc_id))

    def action_done(self, index_name: str, doc_id: str) -> int | None:
        _messageid = self.get_message_id(doc_id)
        _remaining_message_actions = self.actions_by_messageid[_messageid]
        _remaining_message_actions.discard((index_name, doc_id))
        # return the message id only if this was the last action for that message
        return (
            None
            if _remaining_message_actions or (_messageid not in self.fully_scheduled_messageids)
            else _messageid
        )

    def action_errored(self, index_name: str, doc_id: str):
        _messageid = self.messageid_by_docid[doc_id]
        self.errored_messageids.add(_messageid)

    def done_scheduling(self, message_id: int):
        self.fully_scheduled_messageids.add(message_id)

    def forget_message(self, message_id: int):
        del self.actions_by_messageid[message_id]

    def get_message_id(self, doc_id: str):
        return self.messageid_by_docid[doc_id]

    def remaining_done_messages(self):
        for _messageid, _actions in self.actions_by_messageid.items():
            if _messageid not in self.errored_messageids:
                assert not _actions
                yield _messageid
