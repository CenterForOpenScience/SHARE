from __future__ import annotations
import contextlib
import dataclasses
from xml.etree.ElementTree import (
    Element,
    SubElement,
)

from primitive_metadata import primitive_rdf as rdf


__all__ = ('HtmlBuilder',)


@dataclasses.dataclass
class HtmlBuilder:
    given_root: Element
    _: dataclasses.KW_ONLY
    _nested_elements: list[Element] = dataclasses.field(default_factory=list)
    _heading_depth: int = 0

    def __post_init__(self):
        self._nested_elements.append(self.given_root)

    @property
    def root_element(self) -> Element:
        return self._nested_elements[0]

    @property
    def _current_element(self) -> Element:
        return self._nested_elements[-1]

    ###
    # html-building helper methods

    @contextlib.contextmanager
    def nest_h_tag(self, **kwargs):
        _outer_heading_depth = self._heading_depth
        if not _outer_heading_depth:
            self._heading_depth = 1
        elif _outer_heading_depth < 6:  # h6 deepest
            self._heading_depth += 1
        _h_tag = f'h{self._heading_depth}'
        with self.nest(_h_tag, **kwargs) as _nested:
            try:
                yield _nested
            finally:
                self._heading_depth = _outer_heading_depth

    @contextlib.contextmanager
    def nest(self, tag_name, attrs=None):
        _attrs = {**attrs} if attrs else {}
        _nested_element = SubElement(self._current_element, tag_name, _attrs)
        self._nested_elements.append(_nested_element)
        try:
            yield self._current_element
        finally:
            _popped_element = self._nested_elements.pop()
            assert _popped_element is _nested_element

    def leaf(self, tag_name, *, text=None, attrs=None):
        _leaf_element = SubElement(self._current_element, tag_name, attrs or {})
        if isinstance(text, rdf.Literal):
            # TODO: lang
            _leaf_element.text = text.unicode_value
        elif text is not None:
            _leaf_element.text = text
