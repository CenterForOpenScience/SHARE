from __future__ import annotations
import abc
import collections
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
from ._indexnames import parse_indexname_parts


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Elastic8IndexStrategy(IndexStrategy):
    '''abstract base class for index strategies using elasticsearch 8
    '''
    index_definitions: typing.ClassVar[IndexDefinitionDict]

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
        return ChecksumIri.digest_json(
            checksumalgorithm_name='sha-256',
            salt=cls.__name__,
            raw_json={
                _subname: dataclasses.asdict(_def)
                for _subname, _def in cls.current_index_defs().items()
            }
        )

    @classmethod
    @functools.cache
    def current_index_defs(cls):
        # readonly and cached per class
        return types.MappingProxyType(cls.define_current_indexes())

    @classmethod
    @functools.cache
    def _make_elastic8_client(cls) -> elasticsearch8.Elasticsearch:
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
        return self._make_elastic8_client()  # cached shared client

    # abstract method from IndexStrategy
    def each_named_index(self):
        for _subname in self.current_index_defs().keys():
            yield self.get_index_by_subnames(_subname)

    # abstract method from IndexStrategy
    def each_existing_index(self):
        indexname_set = set(
            self.es8_client.indices
            .get(index=self.indexname_wildcard, features=',')
            .keys()
        )
        for indexname in indexname_set:
            _index = self.parse_full_index_name(indexname)
            assert _index.index_strategy == self
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
        _indexnames = self._get_indexnames_for_alias(self._alias_for_searching)
        try:
            _indexname = _indexnames.pop()
        except KeyError:
            return 
        # a SpecificIndex for an alias will work fine for searching, but
        # will error if you try to invoke lifecycle hooks
        return self.get_index_by_subnames(self._alias_for_searching)

    # override from IndexStrategy
    def pls_mark_backfill_complete(self):
        super().pls_mark_backfill_complete()
        # explicit refresh after bulk operation
        self.for_current_index().pls_refresh()

    @property
    def _alias_for_searching(self):
        return f'{self.indexname_prefix}__search'

    @property
    def _alias_for_keeping_live(self):
        return f'{self.indexname_prefix}__live'

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
                        yield {
                            **_elastic_action,
                            '_index': _indexname,
                        }
            action_tracker.done_scheduling(_actionset.message_target_id)

    def _get_indexnames_for_action(
        self,
        index_subname: str,
        *,
        is_backfill_action: bool = False,
    ) -> set[str]:
        if is_backfill_action:
            return {self.get_index_by_subnames(index_subname).full_index_name}
        _indexes_kept_live = self._get_indexnames_for_alias(self._alias_for_keeping_live)

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
        index_strategy: Elastic8IndexStrategy

        # abstract method from IndexStrategy.SpecificIndex
        def pls_get_status(self) -> IndexStatus:
            if not self.pls_check_exists():
                return IndexStatus(
                    index_strategy_name=self.index_strategy.strategy_name,
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
                index_strategy_name=self.index_strategy.strategy_name,
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
            full_index_name = self.full_index_name
            logger.info(f'{self.__class__.__name__}: checking for index {full_index_name}')
            return bool(
                self.index_strategy.es8_client.indices
                .exists(index=full_index_name)
            )

        # abstract method from IndexStrategy.SpecificIndex
        def pls_create(self):
            assert self.is_current, (
                'cannot create a non-current version of an index!'
                ' maybe try `index_strategy.for_current_index()`?'
            )
            index_to_create = self.full_index_name
            logger.debug('Ensuring index %s', index_to_create)
            index_exists = (
                self.index_strategy.es8_client.indices
                .exists(index=index_to_create)
            )
            if not index_exists:
                logger.warning('Creating index %s', index_to_create)
                (
                    self.index_strategy.es8_client.indices
                    .create(
                        index=index_to_create,
                        settings=self.index_strategy.index_settings(),
                        mappings=self.index_strategy.index_mappings(),
                    )
                )
                self.pls_refresh()

        # abstract method from IndexStrategy.SpecificIndex
        def pls_refresh(self):
            (
                self.index_strategy.es8_client.indices
                .refresh(index=self.full_index_name)
            )
            logger.debug('%r: Waiting for yellow status', self)
            (
                self.index_strategy.es8_client.cluster
                .health(wait_for_status='yellow')
            )
            logger.info('%r: Refreshed', self)

        # abstract method from IndexStrategy.SpecificIndex
        def pls_delete(self):
            (
                self.index_strategy.es8_client.indices
                .delete(index=self.full_index_name, ignore=[400, 404])
            )
            logger.warning('%r: deleted', self)

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
