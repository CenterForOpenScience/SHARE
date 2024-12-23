import abc
import dataclasses
from typing import Iterator

from trove import exceptions as trove_exceptions


class ProtoRendering(abc.ABC):
    '''base class for all renderings

    (TODO: typing.Protocol (when py3.12+))
    '''

    @property
    @abc.abstractmethod
    def mediatype(self) -> str:
        '''`mediatype`: required readable attribute
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iter_content(self) -> Iterator[str | bytes | memoryview]:
        '''`iter_content`: (only) required method
        '''
        yield from ()


@dataclasses.dataclass
class SimpleRendering:  # implements ProtoRendering
    mediatype: str
    rendered_content: str = ''

    def iter_content(self):
        yield self.rendered_content


@dataclasses.dataclass
class StreamableRendering:  # implements ProtoRendering
    mediatype: str
    content_stream: Iterator[str | bytes | memoryview]
    _started_already: bool = False

    def iter_content(self):
        if self._started_already:
            raise trove_exceptions.CannotRenderStreamTwice
        self._started_already = True
        yield from self.content_stream
