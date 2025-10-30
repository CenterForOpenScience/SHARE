from __future__ import annotations
from collections.abc import Generator
import contextlib
import dataclasses
from xml.etree.ElementTree import (
    Element,
    SubElement,
    tostring as etree_tostring,
)

from primitive_metadata import primitive_rdf as rdf


__all__ = ('XmlBuilder',)


@dataclasses.dataclass
class XmlBuilder:
    '''XmlBuilder: for building XML (an alternate convenience wrapper around xml.etree)

    >>> _xb = XmlBuilder('foo')
    >>> with _xb.nest('bar', {'blib': 'bloz'}):
    ...   _xb.leaf('baz', text='hello')
    ...   _xb.leaf('boz', {'blib': 'blab'}, text='world')
    >>> str(_xb)
    '''
    root_tag_name: str
    root_attrs: dict = dataclasses.field(default_factory=dict)
    _: dataclasses.KW_ONLY
    _nested_elements: list[Element] = dataclasses.field(repr=False, init=False)

    def __post_init__(self) -> None:
        self._nested_elements = [Element(self.root_tag_name, self.root_attrs)]

    @property
    def root_element(self) -> Element:
        return self._nested_elements[0]

    @property
    def current_element(self) -> Element:
        return self._nested_elements[-1]

    @contextlib.contextmanager
    def nest(self, tag_name: str, attrs: dict | None = None) -> Generator[Element]:
        _attrs = {**attrs} if attrs else {}
        _nested_element = SubElement(self.current_element, tag_name, _attrs)
        self._nested_elements.append(_nested_element)
        try:
            yield self.current_element
        finally:
            _popped_element = self._nested_elements.pop()
            assert _popped_element is _nested_element

    def leaf(self, tag_name: str, attrs: dict | None = None, *, text: str | rdf.Literal | None = None) -> None:
        _leaf_element = SubElement(self.current_element, tag_name, attrs or {})
        if isinstance(text, rdf.Literal):
            # TODO: lang
            _leaf_element.text = text.unicode_value
        elif text is not None:
            _leaf_element.text = text

    def __str__(self) -> str:
        return etree_tostring(self.root_element, encoding='unicode')

    def __bytes__(self) -> bytes:
        return etree_tostring(self.root_element, encoding='utf-8', xml_declaration=True)
