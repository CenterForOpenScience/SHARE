import json

from primitive_metadata import primitive_rdf

from ._base import BaseRenderer


class RdfJsonldRenderer(BaseRenderer):
    MEDIATYPE = 'application/ld+json'

    def render_document(self, data: primitive_rdf.RdfTripleDictionary, focus_iri: str) -> str:
        _jsonld_serializer = primitive_rdf.JsonldSerializer(self.iri_shorthand)
        # TODO: use focus_iri
        return json.dumps(
            _jsonld_serializer.tripledict_as_jsonld(data, with_context=True),
            indent=2,
            sort_keys=True,
        )
