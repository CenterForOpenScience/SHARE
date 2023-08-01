import logging

from django.http.response import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse

from share.admin.util import admin_url
from share.models.index_backfill import IndexBackfill
from share.search.index_messenger import IndexMessenger
from share.search.index_strategy import IndexStrategy


logger = logging.getLogger(__name__)


def search_indexes_view(request):
    if request.method == 'GET':
        return TemplateResponse(
            request,
            'admin/search-indexes.html',
            context={
                'search_url_prefix': _search_url_prefix(),
                'index_status_by_strategy': _index_status_by_strategy(),
            },
        )
    if request.method == 'POST':
        _specific_index = IndexStrategy.get_specific_index(request.POST['specific_indexname'])
        _pls_doer = PLS_DOERS[request.POST['pls_do']]
        _pls_doer(_specific_index)
        _redirect_id = (
            _specific_index.index_strategy.name
            if _pls_doer is _pls_delete
            else _specific_index.indexname
        )
        return HttpResponseRedirect('#'.join((request.path, _redirect_id)))


def _search_url_prefix():
    api_url = reverse('api:search')
    return f'{api_url}?indexStrategy='  # append strategyname or indexname


def _index_status_by_strategy():
    backfill_by_indexname = {
        backfill.specific_indexname: backfill
        for backfill in (
            IndexBackfill.objects
            .filter(index_strategy_name__in=IndexStrategy.all_strategies_by_name().keys())
        )
    }
    status_by_strategy = {}
    for index_strategy in IndexStrategy.all_strategies():
        current_index = index_strategy.for_current_index()
        status_by_strategy[index_strategy.name] = {
            'current': {
                'status': current_index.pls_get_status(),
                'backfill': _serialize_backfill(
                    current_index,
                    backfill_by_indexname.get(current_index.indexname),
                ),
            },
            'prior': sorted((
                specific_index.pls_get_status()
                for specific_index in index_strategy.each_specific_index()
                if not specific_index.is_current
            ), reverse=True),
        }
    return status_by_strategy


def _serialize_backfill(specific_index: IndexStrategy.SpecificIndex, backfill: IndexBackfill):
    if not specific_index.is_current:
        return {}
    if not backfill:
        return {
            'can_start_backfill': specific_index.pls_check_exists(),
        }
    _nonurgent_queue_stats = IndexMessenger().get_queue_stats(
        specific_index.index_strategy.nonurgent_messagequeue_name,
    )
    _phase_messagetypes = specific_index.index_strategy.backfill_phases
    _phase_ratio = f'{backfill.backfill_phase_index + 1}/{len(_phase_messagetypes)}'
    _indexing_and_settled = (
        backfill.backfill_status == IndexBackfill.INDEXING
        and _nonurgent_queue_stats['queue_depth'] == 0
    )
    _next_phase = None
    if _indexing_and_settled and (len(_phase_messagetypes) > backfill.backfill_phase_index + 1):
        _next_phase = _phase_messagetypes[backfill.backfill_phase_index + 1]
    return {
        'backfill_status': backfill.backfill_status,
        'phase_name': _phase_messagetypes[backfill.backfill_phase_index].value,
        'phase_ratio': _phase_ratio,
        'next_phase_name': _next_phase.value if _next_phase else None,
        'backfill_admin_url': admin_url(backfill),
        'backfill_queue_depth': _nonurgent_queue_stats['queue_depth'],
        'backfill_rate': _nonurgent_queue_stats['avg_ack_rate'],
        'can_start_backfill': _next_phase or backfill.backfill_status == IndexBackfill.INITIAL,
        'can_mark_backfill_complete': _indexing_and_settled and not _next_phase,
        'is_complete': (backfill.backfill_status == IndexBackfill.COMPLETE),
    }


def _pls_setup(specific_index):
    assert specific_index.is_current
    specific_index.pls_setup()


def _pls_start_keeping_live(specific_index):
    specific_index.pls_start_keeping_live()


def _pls_stop_keeping_live(specific_index):
    specific_index.pls_stop_keeping_live()


def _pls_start_backfill(specific_index):
    assert specific_index.is_current
    specific_index.index_strategy.pls_start_backfill()


def _pls_mark_backfill_complete(specific_index):
    specific_index.index_strategy.pls_mark_backfill_complete()


def _pls_make_default_for_searching(specific_index):
    specific_index.index_strategy.pls_make_default_for_searching(specific_index)


def _pls_delete(specific_index):
    assert not specific_index.is_current
    specific_index.pls_delete()


PLS_DOERS = {
    'setup': _pls_setup,
    'start_keeping_live': _pls_start_keeping_live,
    'start_backfill': _pls_start_backfill,
    'mark_backfill_complete': _pls_mark_backfill_complete,
    'make_default_for_searching': _pls_make_default_for_searching,
    'stop_keeping_live': _pls_stop_keeping_live,
    'delete': _pls_delete,
}
