import abc

from gather import primitive_rdf


class BaseRdfExtractor(abc.ABC):
    def __init__(self, source_config):
        self.source_config = source_config

    @abc.abstractmethod
    def extract_rdf(self, input_document: str) -> primitive_rdf.RdfTripleDictionary:
        raise NotImplementedError
