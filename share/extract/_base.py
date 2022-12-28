import abc
import typing

import rdflib


class BaseRdfExtractor(abc.ABC):
    def __init__(self, source_config, input_document):
        self.source_config = source_config
        self.input_document = input_document

    @abc.abstractmethod
    def extract_resource_identifiers(self) -> typing.Iterable[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def extract_resource_description(self, resource_identifier: str) -> rdflib.Graph:
        raise NotImplementedError
