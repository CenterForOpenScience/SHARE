import abc
from typing import Any
from primitive_metadata import primitive_rdf

from trove.models.resource_description import ResourceDescription


class IndexcardDeriver(abc.ABC):
    upstream_description: ResourceDescription
    focus_iri: str
    data: primitive_rdf.RdfGraph

    def __init__(self, upstream_description: ResourceDescription):
        self.upstream_description = upstream_description
        self.focus_iri = upstream_description.focus_iri
        self.data = upstream_description.as_rdfdoc_with_supplements()

    def q(self, pathset: Any) -> Any:
        # convenience for querying self.data on self.focus_iri
        return self.data.q(self.focus_iri, pathset)

    ###
    # for subclasses to implement:

    @staticmethod
    @abc.abstractmethod
    def deriver_iri() -> str:
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def derived_datatype_iris() -> tuple[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def should_skip(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def derive_card_as_text(self) -> str:
        raise NotImplementedError
