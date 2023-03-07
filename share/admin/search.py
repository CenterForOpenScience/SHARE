from django.http.response import HttpResponseRedirect
from django.template.response import TemplateResponse

from share.search.index_strategy import IndexStrategy


def search_indexes_view(request):
    if request.method == 'GET':
        return TemplateResponse(
            request,
            'admin/search-indexes.html',
            context={
                'search_index_statuses': _search_index_statuses(),
            },
        )
    if request.method == 'POST':
        specific_index_name = request.POST['specific_index_name']
        pls_doer = PLS_DOERS[request.POST['pls_do']]
        pls_doer(specific_index_name)
        return HttpResponseRedirect('')


def _search_index_statuses():
    statuses = {}
    for index_strategy in IndexStrategy.all_strategies().values():
        statuses[index_strategy.name] = index_strategy.specific_index_statuses()
    return statuses


def _pls_setup(specific_index_name):
    index_strategy = IndexStrategy.by_request(specific_index_name)
    assert index_strategy.current_index_name == specific_index_name
    index_strategy.pls_setup_as_needed()


def _pls_open_for_searching(specific_index_name):
    index_strategy = IndexStrategy.by_request(specific_index_name)
    index_strategy.pls_open_for_searching()


def _pls_organize_fill(specific_index_name):
    index_strategy = IndexStrategy.by_request(specific_index_name)
    assert index_strategy.current_index_name == specific_index_name
    index_strategy.pls_organize_backfill()


def _pls_delete(specific_index_name):
    index_strategy = IndexStrategy.by_request(specific_index_name)
    index_strategy.pls_delete()


PLS_DOERS = {
    'setup': _pls_setup,
    'open_for_searching': _pls_open_for_searching,
    'organize_fill': _pls_organize_fill,
    'delete': _pls_delete,
}
