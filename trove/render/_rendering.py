import abc
import dataclasses
from typing import Iterator

from primitive_metadata import primitive_rdf as rdf

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


@dataclasses.dataclass
class LiteralRendering(ProtoRendering):
    literal: rdf.Literal
    # (TODO: languages)

    @property
    def mediatype(self) -> str:
        try:
            return next(
                rdf.iri_minus_namespace(_iri, namespace=rdf.IANA_MEDIATYPE)
                for _iri in self.literal.datatype_iris
                if _iri in rdf.IANA_MEDIATYPE
            )
        except StopIteration:  # no mediatype iri
            return 'text/plain; charset=utf-8'

    def iter_content(self):
        yield self.literal.unicode_value
