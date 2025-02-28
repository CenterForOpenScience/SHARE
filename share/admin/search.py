import logging

from django.http.response import HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse

from share.admin.util import admin_url
from share.models.index_backfill import IndexBackfill
from share.search.index_messenger import IndexMessenger
from share.search.index_strategy import (
    IndexStrategy,
    all_strategy_names,
    each_strategy,
    parse_strategy_name,
    parse_specific_index_name,
)


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
        _index_strategy = parse_strategy_name(request.POST['strategy_name'])
        _pls_doer = PLS_DOERS[request.POST['pls_do']]
        _pls_doer(_index_strategy, request.POST)
        _redirect_id = _index_strategy.strategy_name
        return HttpResponseRedirect('#'.join((request.path, _redirect_id)))


def search_index_mappings_view(request, index_name):
    _specific_index = parse_specific_index_name(index_name)
    _mappings = _specific_index.pls_get_mappings()
    return JsonResponse(_mappings)


def _search_url_prefix():
    api_url = reverse('api:search')
    return f'{api_url}?indexStrategy='  # append strategyname or indexname


def _mappings_url_prefix():
    return '/admin/search-index-mappings/'


def _index_status_by_strategy():
    _backfill_by_checksum: dict[str, IndexBackfill] = {
        _backfill.strategy_checksum: _backfill
        for _backfill in (
            IndexBackfill.objects
            .filter(index_strategy_name__in=all_strategy_names())
        )
    }
    status_by_strategy = {}
    _messenger = IndexMessenger()
    for _index_strategy in each_strategy():
        _current_backfill = (
            _backfill_by_checksum.get(str(_index_strategy.CURRENT_STRATEGY_CHECKSUM))
            or _backfill_by_checksum.get(_index_strategy.indexname_prefix)  # backcompat
        )
        status_by_strategy[_index_strategy.strategy_name] = {
            'status': _index_strategy.pls_get_strategy_status(),
            'backfill': _serialize_backfill(_index_strategy, _current_backfill),
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
    strategy: IndexStrategy,
    backfill: IndexBackfill | None,
):
    if not strategy.is_current:
        return {}
    if not backfill:
        return {
            'can_start_backfill': strategy.pls_check_exists(),
        }
    return {
        'backfill_status': backfill.backfill_status,
        'backfill_admin_url': admin_url(backfill),
        'can_start_backfill': (backfill.backfill_status == IndexBackfill.INITIAL),
        'can_mark_backfill_complete': (backfill.backfill_status == IndexBackfill.INDEXING),
        'is_complete': (backfill.backfill_status == IndexBackfill.COMPLETE),
    }


def _pls_setup(index_strategy: IndexStrategy, request_kwargs):
    assert index_strategy.is_current
    index_strategy.pls_setup()


def _pls_start_keeping_live(index_strategy: IndexStrategy, request_kwargs):
    index_strategy.pls_start_keeping_live()


def _pls_stop_keeping_live(index_strategy: IndexStrategy, request_kwargs):
    index_strategy.pls_stop_keeping_live()


def _pls_start_backfill(index_strategy: IndexStrategy, request_kwargs):
    assert index_strategy.is_current
    index_strategy.pls_start_backfill()


def _pls_mark_backfill_complete(index_strategy: IndexStrategy, request_kwargs):
    index_strategy.pls_mark_backfill_complete()


def _pls_make_default_for_searching(index_strategy: IndexStrategy, request_kwargs):
    index_strategy.pls_make_default_for_searching()


def _pls_delete(index_strategy: IndexStrategy, request_kwargs):
    if request_kwargs.get('really') == 'really really':
        index_strategy.pls_teardown()


PLS_DOERS = {
    'setup': _pls_setup,
    'start_keeping_live': _pls_start_keeping_live,
    'start_backfill': _pls_start_backfill,
    'mark_backfill_complete': _pls_mark_backfill_complete,
    'make_default_for_searching': _pls_make_default_for_searching,
    'stop_keeping_live': _pls_stop_keeping_live,
    'delete': _pls_delete,
}
