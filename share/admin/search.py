import logging

from django.http.response import HttpResponseRedirect
from django.template.response import TemplateResponse

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
                'index_status_by_strategy': _index_status_by_strategy(),
            },
        )
    if request.method == 'POST':
        specific_indexname = request.POST['specific_indexname']
        pls_doer = PLS_DOERS[request.POST['pls_do']]
        pls_doer(specific_indexname)
        return HttpResponseRedirect('')


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
    nonurgent_queue_size = IndexMessenger().get_queue_depth(
        specific_index.index_strategy.nonurgent_messagequeue_name,
    )
    return {
        'backfill_status': backfill.backfill_status,
        'backfill_modified': backfill.modified.isoformat(timespec='minutes'),
        'backfill_admin_url': admin_url(backfill),
        'backfill_queue_depth': nonurgent_queue_size,
        'can_start_backfill': (backfill.backfill_status == IndexBackfill.INITIAL),
        'can_mark_backfill_complete': (
            backfill.backfill_status == IndexBackfill.INDEXING
            and nonurgent_queue_size == 0
        ),
        'is_complete': (backfill.backfill_status == IndexBackfill.COMPLETE),
    }


def _pls_create(specific_indexname):
    specific_index = IndexStrategy.get_specific_index(specific_indexname)
    assert specific_index.is_current
    specific_index.pls_create()


def _pls_start_keeping_live(specific_indexname):
    specific_index = IndexStrategy.get_specific_index(specific_indexname)
    specific_index.pls_start_keeping_live()


def _pls_stop_keeping_live(specific_indexname):
    specific_index = IndexStrategy.get_specific_index(specific_indexname)
    specific_index.pls_stop_keeping_live()


def _pls_start_backfill(specific_indexname):
    specific_index = IndexStrategy.get_specific_index(specific_indexname)
    assert specific_index.is_current
    specific_index.index_strategy.pls_start_backfill()


def _pls_mark_backfill_complete(specific_indexname):
    specific_index = IndexStrategy.get_specific_index(specific_indexname)
    specific_index.index_strategy.pls_mark_backfill_complete()


def _pls_make_default_for_searching(specific_indexname):
    specific_index = IndexStrategy.get_specific_index(specific_indexname)
    specific_index.index_strategy.pls_make_default_for_searching(specific_index)


def _pls_delete(specific_indexname):
    specific_index = IndexStrategy.get_specific_index(specific_indexname)
    assert not specific_index.is_current
    specific_index.pls_delete()


PLS_DOERS = {
    'create': _pls_create,
    'start_keeping_live': _pls_start_keeping_live,
    'start_backfill': _pls_start_backfill,
    'mark_backfill_complete': _pls_mark_backfill_complete,
    'make_default_for_searching': _pls_make_default_for_searching,
    'stop_keeping_live': _pls_stop_keeping_live,
    'delete': _pls_delete,
}
