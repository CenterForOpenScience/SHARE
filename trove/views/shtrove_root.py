from primitive_metadata import primitive_rdf as rdf
from django.conf import settings

from trove.vocab import namespaces as ns
from ._base import StaticTroveView


class ShtroveRootView(StaticTroveView):
    @classmethod
    def get_focus_iri(cls):
        return settings.SHARE_WEB_URL

    @classmethod
    def get_static_triples(cls, focus_iri: str) -> rdf.RdfTripleDictionary:
        _here = rdf.IriNamespace(focus_iri)
        return {
            focus_iri: {
                ns.DCTERMS.description: {
                    rdf.literal('a trove of metadata meant to be shared', language='en'),
                },
                ns.RDFS.seeAlso: {
                    _here['trove/docs'],
                    _here['trove/browse'],
                    _here['trove/index-card-search'],
                },
            },
        }
