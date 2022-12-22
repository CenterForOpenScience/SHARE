from share.metadata_formats.base import MetadataFormatter


class RdfTurtleFormatter(MetadataFormatter):
    """builds an RDF graph and serializes it as turtle
    """

    def format(self, normalized_datum):
        assert normalized_datum._RDF_FORMAT == 'turtle'
        if normalized_datum.serialized_rdf is None:
            normalized_datum.convert_to_rdf()
        return normalized_datum.serialized_rdf

        # TODO
        # if (
        #     not central_work
        #     or central_work.concrete_type != 'abstractcreativework'
        #     or central_work['is_deleted']
        # ):
        #     return self.format_as_deleted(None)
