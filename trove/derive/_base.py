import abc

from gather import primitive_rdf

from trove.models import IndexcardRdf


class IndexcardDeriver(abc.ABC):
    upriver_rdf: IndexcardRdf
    focus_iri: str
    data: primitive_rdf.TripledictWrapper

    def __init__(self, upriver_rdf: IndexcardRdf):
        self.upriver_rdf = upriver_rdf
        self.focus_iri = upriver_rdf.focus_iri
        self.data = primitive_rdf.TripledictWrapper(upriver_rdf.as_rdf_tripledict())

    ###
    # for subclasses to implement:

    @staticmethod
    @abc.abstractmethod
    def deriver_iri() -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def should_skip(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def derive_card_as_text(self) -> str:
        raise NotImplementedError
