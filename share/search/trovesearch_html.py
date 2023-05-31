import contextlib
import datetime
from xml.etree.ElementTree import TreeBuilder, tostring

import gather


def tripledict_as_html(tripledict: gather.RdfTripleDictionary, *, focus) -> str:
    # TODO: microdata, css, language tags
    _html_builder = TreeBuilder()
    # define some local helpers:

    @contextlib.contextmanager
    def _nest_element(tag_name, attrs=None):
        _html_builder.start(tag_name, attrs or {})
        yield
        _html_builder.end(tag_name)

    def _leaf_element(tag_name, *, text=None, attrs=None):
        _html_builder.start(tag_name, attrs or {})
        if text is not None:
            _html_builder.data(text)
        _html_builder.end(tag_name)

    def _twoples_list(twoples: gather.RdfTwopleDictionary, attrs=None):
        with _nest_element('ul', (attrs or {})):
            for _pred, _obj_set in twoples.items():
                with _nest_element('li'):
                    _leaf_element('span', text=_pred)  # TODO: <a href>
                    with _nest_element('ul'):
                        for _obj in _obj_set:
                            with _nest_element('li'):
                                _obj_element(_obj)

    def _obj_element(obj: gather.RdfObject):
        if isinstance(obj, frozenset):
            _twoples_list(gather.unfreeze_blanknode(obj))
        elif isinstance(obj, gather.Text):
            # TODO language tag
            _leaf_element('span', text=str(obj))
        elif isinstance(obj, str):
            # TODO link to anchor on this page?
            _leaf_element('a', text=obj)
        elif isinstance(obj, (float, int, datetime.date)):
            # TODO datatype?
            _leaf_element('span', text=str(obj))

    # now use those helpers to build an <article>
    # with all the info gathered in this gathering
    with _nest_element('article'):
        # TODO: shortened display names
        # TODO: start with focus
        for _subj, _twopledict in tripledict.items():
            with _nest_element('section'):
                _leaf_element('h2', text=_subj)
                _twoples_list(_twopledict)
    # and serialize as str
    return tostring(
        _html_builder.close(),
        encoding='unicode',
        method='html',
    )
