from gather import primitive_rdf

from ._base import BaseRdfExtractor


class TurtleRdfExtractor(BaseRdfExtractor):
    def extract_rdf(self, input_document):
        return primitive_rdf.tripledict_from_turtle(input_document)
