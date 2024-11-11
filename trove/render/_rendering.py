import dataclasses
from typing import Iterable

from primitive_metadata import primitive_rdf as rdf


class ProtoRendering:
    '''base class for all renderings'''

    @property
    def mediatype(self) -> str:
        raise NotImplementedError

    @property
    def is_streamed(self) -> bool:
        return False

    def iter_content(self) -> Iterable[str | bytes | memoryview]:
        yield from ()


@dataclasses.dataclass
class LiteralRendering(ProtoRendering):
    literal: rdf.Literal
    # (TODO: language(s))

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
