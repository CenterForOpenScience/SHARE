from __future__ import annotations
from collections.abc import Generator
import contextlib
import dataclasses
from xml.etree.ElementTree import tostring as etree_tostring

from trove.util.xml import XmlBuilder


__all__ = ('HtmlBuilder',)

HTML_DOCTYPE = '<!DOCTYPE html>'


@dataclasses.dataclass
class HtmlBuilder(XmlBuilder):
    root_tag_name: str = 'html'
    _: dataclasses.KW_ONLY
    _heading_depth: int = 0

    ###
    # html-building helper methods

    @contextlib.contextmanager
    def deeper_heading(self) -> Generator[str]:
        _outer_heading_depth = self._heading_depth
        if not _outer_heading_depth:
            self._heading_depth = 1
        elif _outer_heading_depth < 6:  # h6 deepest
            self._heading_depth += 1
        try:
            yield f'h{self._heading_depth}'
        finally:
            self._heading_depth = _outer_heading_depth

    def as_html_doc(self) -> str:
        return '\n'.join((HTML_DOCTYPE, str(self)))

    def __str__(self) -> str:
        return etree_tostring(self.root_element, encoding='unicode', method='html')

    def __bytes__(self) -> bytes:
        return etree_tostring(self.root_element, encoding='utf-8', method='html')
