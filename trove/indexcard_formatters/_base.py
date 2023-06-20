import abc
import typing

from trove.models import RdfIndexcard


class IndexcardFormatter(abc.ABC):
    FORMAT_IRI = None

    @abc.abstractmethod
    def pls_format_indexcard(self, rdf_indexcard: RdfIndexcard) -> typing.Optional[str]:
        raise NotImplementedError
