from share.util import rdfutil
from ._base import BaseRdfExtractor


class SimpleRdfParseExtractor(BaseRdfExtractor):
    def __init__(self, *args, rdf_parser, **kwargs):
        self._rdf_parser = rdf_parser
        return super().__init__(*args, **kwargs)

    def extract_rdf(self, input_str):
        return rdfutil.contextualized_graph().parse(
            format=self._rdf_parser,
            data=input_str,
        )
