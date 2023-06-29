import abc

import gather

from trove.models import RdfIndexcard


class IndexcardDeriver(abc.ABC):
    upriver_card: RdfIndexcard
    focus_iri: str
    tripledict: gather.RdfTripleDictionary

    def __init__(self, upriver_card: RdfIndexcard):
        self.upriver_card = upriver_card
        self.focus_iri = upriver_card.focus_iri
        self.tripledict = upriver_card.as_rdf_tripledict()

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
