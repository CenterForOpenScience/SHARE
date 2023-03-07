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
        index_name = request.POST['index_name']
        specific_index_name = request.POST['specific_index_name']
        pls_doer = PLS_DOERS[request.POST['pls_do']]
        pls_doer(index_name=index_name, specific_index_name=specific_index_name)
        return HttpResponseRedirect('')


def _search_index_statuses():
    statuses = {}
    for index_strategy in IndexStrategy.for_all_indexes():
        statuses[index_strategy.name] = index_strategy.specific_index_statuses()
    return statuses


def _pls_setup(index_name, specific_index_name):
    index_strategy = IndexStrategy.by_name(index_name)
    assert index_strategy.current_index_name == specific_index_name
    index_strategy.pls_setup_as_needed()


def _pls_make_prime(index_name, specific_index_name):
    index_strategy = IndexStrategy.by_name(index_name)
    index_strategy.pls_open_for_searching(specific_index_name=specific_index_name)


def _pls_organize_fill(index_name, specific_index_name):
    index_strategy = IndexStrategy.by_name(index_name)
    assert index_strategy.current_index_name == specific_index_name
    index_strategy.pls_organize_backfill()


def _pls_delete(index_name, specific_index_name):
    index_strategy = IndexStrategy.by_name(index_name)
    index_strategy.pls_delete(specific_index_name=specific_index_name)


PLS_DOERS = {
    'setup': _pls_setup,
    'make_prime': _pls_make_prime,
    'organize_fill': _pls_organize_fill,
    'delete': _pls_delete,
}
