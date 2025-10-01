from collections.abc import Iterator
import dataclasses

from trove import exceptions as trove_exceptions
from .proto import ProtoRendering


@dataclasses.dataclass
class StreamableRendering(ProtoRendering):
    mediatype: str
    content_stream: Iterator[str] | Iterator[bytes] = iter(())
    _started_already: bool = False

    def iter_content(self) -> Iterator[str] | Iterator[bytes]:
        if self._started_already:
            raise trove_exceptions.CannotRenderStreamTwice
        self._started_already = True
        yield from self.content_stream
