from collections.abc import Generator
import dataclasses

from .proto import ProtoRendering

__all__ = ('EntireRendering',)


@dataclasses.dataclass
class EntireRendering(ProtoRendering):
    '''EntireRendering: for response content rendered in its entirety before being sent
    '''
    mediatype: str
    entire_content: str | bytes = ''

    def iter_content(self) -> Generator[str] | Generator[bytes]:
        yield self.entire_content
