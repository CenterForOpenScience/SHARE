import abc
import typing

import rdflib


class BaseRdfExtractor(abc.ABC):
    def __init__(self, source_config):
        self.source_config = source_config

    @abc.abstractmethod
    def extract_rdf(self, input_str: str) -> typing.Optional[rdflib.Graph]:
        raise NotImplementedError
