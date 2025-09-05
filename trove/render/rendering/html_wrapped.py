import dataclasses
import html
from typing import Iterator

from trove.vocab import mediatypes
from trove.render._html import HTML_DOCTYPE
from .proto import ProtoRendering


@dataclasses.dataclass
class HtmlWrappedRendering(ProtoRendering):
    inner_rendering: ProtoRendering
    mediatype: str = mediatypes.HTML

    def iter_content(self) -> Iterator[str]:
        yield HTML_DOCTYPE
        yield '<pre>'
        for _content in self.inner_rendering.iter_content():
            yield html.escape(_content)
        yield '</pre>'
