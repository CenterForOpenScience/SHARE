
from share.metadata_formats.base import MetadataFormatter


class TurtleFormatter(MetadataFormatter):
    def format(self, normalized_datum):
        assert normalized_datum._RDF_FORMAT == 'turtle'
        if normalized_datum.serialized_rdfgraph is None:
            normalized_datum.convert_to_rdf()
        if normalized_datum.serialized_rdfgraph == '':
            return None  # should be deleted from the index
        return normalized_datum.serialized_rdfgraph
