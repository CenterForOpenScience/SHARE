from share.metadata_formats.base import MetadataFormatter


class RdfTurtleFormatter(MetadataFormatter):
    def format(self, normalized_datum):
        assert normalized_datum._RDF_FORMAT == 'turtle'
        if normalized_datum.serialized_rdfgraph is None:
            normalized_datum.convert_to_rdf()
        return normalized_datum.serialized_rdfgraph
