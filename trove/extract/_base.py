import abc

from primitive_metadata import primitive_rdf


class BaseRdfExtractor(abc.ABC):
    @abc.abstractmethod
    def extract_rdf(self, input_document: str) -> primitive_rdf.RdfTripleDictionary:
        raise NotImplementedError
