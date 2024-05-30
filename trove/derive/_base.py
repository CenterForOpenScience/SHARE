import abc

from primitive_metadata import primitive_rdf

from trove.models import IndexcardRdf


class IndexcardDeriver(abc.ABC):
    upriver_rdf: IndexcardRdf
    focus_iri: str
    data: primitive_rdf.RdfGraph

    def __init__(self, upriver_rdf: IndexcardRdf):
        self.upriver_rdf = upriver_rdf
        self.focus_iri = upriver_rdf.focus_iri
        self.data = primitive_rdf.RdfGraph(upriver_rdf.as_rdf_tripledict())

    def q(self, pathset):
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
