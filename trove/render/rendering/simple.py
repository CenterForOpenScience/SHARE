from collections.abc import Generator
import dataclasses

from .proto import ProtoRendering

__all__ = ('SimpleRendering',)


@dataclasses.dataclass
class SimpleRendering(ProtoRendering):
    '''for simple pre-rendered string content
    '''
    mediatype: str
    rendered_content: str | bytes = ''

    def iter_content(self) -> Generator[str] | Generator[bytes]:
        yield self.rendered_content
