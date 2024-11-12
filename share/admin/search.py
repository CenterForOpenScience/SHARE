import logging

from django.http.response import HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse

from share.admin.util import admin_url
from share.models.index_backfill import IndexBackfill
from share.search.index_messenger import IndexMessenger
from share.search import index_strategy


logger = logging.getLogger(__name__)


def search_indexes_view(request):
    if request.method == 'GET':
        return TemplateResponse(
            request,
            'admin/search-indexes.html',
            context={
                'search_url_prefix': _search_url_prefix(),
                'mappings_url_prefix': _mappings_url_prefix(),
                'index_status_by_strategy': _index_status_by_strategy(),
            },
        )
    if request.method == 'POST':
        _specific_index = index_strategy.get_specific_index(request.POST['specific_indexname'])
        _pls_doer = PLS_DOERS[request.POST['pls_do']]
        _pls_doer(_specific_index)
        _redirect_id = (
            _specific_index.index_strategy.name
            if _pls_doer is _pls_delete
            else _specific_index.indexname
        )
        return HttpResponseRedirect('#'.join((request.path, _redirect_id)))


def search_index_mappings_view(request, index_name):
    _specific_index = index_strategy.get_specific_index(index_name)
    _mappings = _specific_index.pls_get_mappings()
    return JsonResponse(_mappings)


def _search_url_prefix():
    api_url = reverse('api:search')
    return f'{api_url}?indexStrategy='  # append strategyname or indexname


def _mappings_url_prefix():
    return '/admin/search-index-mappings/'


def _index_status_by_strategy():
    backfill_by_indexname: dict[str, IndexBackfill] = {
        backfill.specific_indexname: backfill
        for backfill in (
            IndexBackfill.objects
            .filter(index_strategy_name__in=index_strategy.all_index_strategies().keys())
        )
    }
    status_by_strategy = {}
    _messenger = IndexMessenger()
    for _index_strategy in index_strategy.all_index_strategies().values():
        current_index = _index_strategy.for_current_index()
        status_by_strategy[_index_strategy.name] = {
            'current': {
                'status': current_index.pls_get_status(),
                'backfill': _serialize_backfill(
                    current_index,
                    backfill_by_indexname.get(current_index.indexname),
                ),
            },
            'prior': sorted((
                specific_index.pls_get_status()
                for specific_index in _index_strategy.each_specific_index()
                if not specific_index.is_current
            ), reverse=True),
            'queues': [
                {
                    'name': _queue_name,
                    **_messenger.get_queue_stats(_queue_name),
                }
                for _queue_name in (
                    _index_strategy.urgent_messagequeue_name,
                    _index_strategy.nonurgent_messagequeue_name,
                )
            ],
        }
    return status_by_strategy


def _serialize_backfill(
    specific_index: index_strategy.IndexStrategy.SpecificIndex,
    backfill: IndexBackfill | None,
):
    if not specific_index.is_current:
        return {}
    if not backfill:
        return {
            'can_start_backfill': specific_index.pls_check_exists(),
        }
    return {
        'backfill_status': backfill.backfill_status,
        'backfill_admin_url': admin_url(backfill),
        'can_start_backfill': (backfill.backfill_status == IndexBackfill.INITIAL),
        'can_mark_backfill_complete': (backfill.backfill_status == IndexBackfill.INDEXING),
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
