from primitive_metadata import gather

from trove.trovesearch.search_params import BaseTroveParams


def ask_gathering_from_params(
    gathering: gather.Gathering,
    params: BaseTroveParams,
    start_focus: gather.Focus,
):
    # fill the gathering's cache with included related resources...
    gathering.ask(params.included_relations, focus=start_focus)
    # ...and add requested attributes on the focus and related resources
    for _focus in gathering.cache.focus_set:
        for _focustype in _focus.type_iris:
            try:
                _attrpaths = params.attrpaths_by_type[_focustype]
            except KeyError:
                pass  # no attribute fields for this type
            else:
                gathering.ask(_attrpaths, focus=_focus)
