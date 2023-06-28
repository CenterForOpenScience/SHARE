import abc
import typing

from trove.models import RdfIndexcard


class IndexcardDerivation(abc.ABC):
    @abc.abstractmethod
    def pls_derive_indexcard(self, rdf_indexcard: RdfIndexcard) -> typing.Optional[str]:
        raise NotImplementedError
