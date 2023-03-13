from django.http.response import HttpResponseRedirect
from django.template.response import TemplateResponse

from share.admin.util import admin_url
from share.models.index_backfill import IndexBackfill
from share.search.index_strategy import IndexStrategy


def search_indexes_view(request):
    if request.method == 'GET':
        return TemplateResponse(
            request,
            'admin/search-indexes.html',
            context={
                'indexes_by_strategy': _indexes_by_strategy(),
            },
        )
    if request.method == 'POST':
        specific_indexname = request.POST['specific_indexname']
        pls_doer = PLS_DOERS[request.POST['pls_do']]
        pls_doer(specific_indexname)
        return HttpResponseRedirect('')


def _indexes_by_strategy():
    status_by_strategy = {}
    backfill_by_index = _backfill_by_index()
    for index_strategy in IndexStrategy.all_strategies().values():
        status_by_strategy[index_strategy.name] = [
            (index_status, backfill_by_index.get(index_status.specific_indexname))
            for index_status in index_strategy.specific_index_statuses()
        ]
    return status_by_strategy


def _backfill_by_index():
    all_strategies = IndexStrategy.all_strategies()
    backfill_by_index = {}
    for backfill in IndexBackfill.objects.filter(index_strategy_name__in=all_strategies.keys()):
        current_indexname = all_strategies[backfill.index_strategy_name].indexname
        backfill_by_index[backfill.specific_indexname] = {
            'can_start_backfill': (
                backfill.specific_indexname == current_indexname
                and backfill.backfill_status == IndexBackfill.INITIAL
            ),
            'can_mark_backfill_complete': (backfill.backfill_status == IndexBackfill.INDEXING),
            'is_complete': (backfill.backfill_status == IndexBackfill.COMPLETE),
            'backfill_status': backfill.backfill_status,
            'backfill_modified': backfill.modified.isoformat(timespec='minutes'),
            'backfill_admin_url': admin_url(backfill),
        }
    for index_strategy in all_strategies.values():
        if (
            index_strategy.SUPPORTS_BACKFILL
            and index_strategy.indexname not in backfill_by_index
            and index_strategy.pls_check_exists()
        ):
            backfill_by_index[index_strategy.indexname] = {
                'can_start_backfill': True,
            }
    return backfill_by_index


def _pls_create(specific_indexname):
    index_strategy = IndexStrategy.by_request(specific_indexname)
    index_strategy.assert_setup_is_current()
    index_strategy.pls_setup_as_needed()


def _pls_keep_live(specific_indexname):
    index_strategy = IndexStrategy.by_request(specific_indexname)
    index_strategy.pls_keep_live()


def _pls_stop_keeping_live(specific_indexname):
    index_strategy = IndexStrategy.by_request(specific_indexname)
    index_strategy.pls_stop_keeping_live()


def _pls_start_backfill(specific_indexname):
    index_strategy = IndexStrategy.by_request(specific_indexname)
    index_strategy.assert_setup_is_current()
    index_strategy.pls_start_backfill()


def _pls_mark_backfill_complete(specific_indexname):
    index_strategy = IndexStrategy.by_request(specific_indexname)
    index_strategy.pls_mark_backfill_complete()


def _pls_make_default_for_searching(specific_indexname):
    index_strategy = IndexStrategy.by_request(specific_indexname)
    index_strategy.pls_make_default_for_searching()


def _pls_delete(specific_indexname):
    index_strategy = IndexStrategy.by_request(specific_indexname)
    assert not index_strategy.is_current
    index_strategy.pls_delete()


PLS_DOERS = {
    'create': _pls_create,
    'keep_live': _pls_keep_live,
    'start_backfill': _pls_start_backfill,
    'mark_backfill_complete': _pls_mark_backfill_complete,
    'make_default_for_searching': _pls_make_default_for_searching,
    'stop_keeping_live': _pls_stop_keeping_live,
    'delete': _pls_delete,
}
