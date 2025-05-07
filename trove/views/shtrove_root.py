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
        _docs = _here['trove/docs']
        _browse = _here['trove/browse']
        _cardsearch = _here['trove/index-card-search']
        return {
            focus_iri: {
                ns.DCTERMS.description: {
                    rdf.literal('a trove of metadata meant to be shared', language='en'),
                },
                ns.RDFS.seeAlso: {_docs, _browse, _cardsearch},
            },
            _docs: {
                ns.DCTERMS.title: {rdf.literal('trove search-api docs', language='en')},
            },
            _browse: {
                ns.DCTERMS.title: {rdf.literal('trove browse', language='en')},
            },
            _cardsearch: {
                ns.DCTERMS.title: {rdf.literal('trove index-card-search', language='en')},
            },
        }
