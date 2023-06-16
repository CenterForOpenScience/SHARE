import gather

from ._base import BaseRdfExtractor


class TurtleRdfExtractor(BaseRdfExtractor):
    def extract_rdf(self, input_document):
        return gather.tripledict_from_turtle(input_document)
