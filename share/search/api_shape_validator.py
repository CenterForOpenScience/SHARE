import dataclasses
import pathlib

import pyshacl
import rdflib


@dataclasses.dataclass
class ShaclValidationReport:
    # for the three-tuple returned by pyshacl.validate
    conforms: bool
    results_graph: rdflib.Graph
    results_text: str


class ApiShapeValidator:
    API_SHACL_SHAPES_FILENAME = 'api_shacl_shapes.ttl'

    @classmethod
    def shacl_graph(cls):
        try:
            return cls.__shacl_graph
        except AttributeError:
            shacl_file_path = pathlib.Path(__file__).parent.joinpath(cls.API_SHACL_SHAPES_FILENAME)
            with open(shacl_file_path) as shacl_file:
                cls.__shacl_graph = rdflib.Graph().parse(shacl_file)
            return cls.__shacl_graph

    def validate(self, data_graph) -> ShaclValidationReport:
        return ShaclValidationReport(*pyshacl.validate(
            data_graph=data_graph,
            shacl_graph=self.shacl_graph(),
            meta_shacl=__debug__,  # if __debug__, validate shacl_graph too
        ))
