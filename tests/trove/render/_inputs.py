import dataclasses
import datetime
import json

import primitive_metadata.primitive_rdf as rdf

from trove.vocab.namespaces import (
    DCAT,
    DCTERMS,
    FOAF,
    RDF,
    TROVE,
    BLARG,
)


@dataclasses.dataclass
class RdfCase:
    focus: str
    tripledict: rdf.RdfTripleDictionary


UNRENDERED_RDF = {
    'simple_card': RdfCase(BLARG.aCard, {
        BLARG.aCard: {
            RDF.type: {TROVE.Indexcard, DCAT.CatalogRecord},
            FOAF.primaryTopic: {BLARG.anItem},
            TROVE.focusIdentifier: {rdf.literal(BLARG.anItem)},
            DCTERMS.issued: {rdf.literal(datetime.date(2024, 1, 1))},
            DCTERMS.modified: {rdf.literal(datetime.date(2024, 1, 1))},
            TROVE.resourceMetadata: {rdf.literal(
                json.dumps({'@id': BLARG.anItem, 'title': 'an item, yes'}),
                datatype_iris=RDF.JSON,
            )},
        },
    }),
    'various_types': RdfCase(BLARG.aSubject, {
        BLARG.aSubject: {
            RDF.type: {BLARG.aType},
            BLARG.hasIri: {BLARG.anIri},
            BLARG.hasRdfStringLiteral: {rdf.literal('an rdf:string literal')},
            BLARG.hasRdfLangStringLiteral: {rdf.literal('a rdf:langString literal', language='en')},
            BLARG.hasIntegerLiteral: {rdf.literal(17)},
            BLARG.hasDateLiteral: {rdf.literal(datetime.date(2024, 1, 1))},
            BLARG.hasStrangeLiteral: {rdf.literal('a literal of strange datatype', datatype_iris=BLARG.aStrangeDatatype)},
        },
    }),
}


UNRENDERED_SEARCH_RDF = {
    'no_results': RdfCase(BLARG.aSearch, {
        BLARG.aSearch: {
            RDF.type: {TROVE.Cardsearch},
            TROVE.totalResultCount: {rdf.literal(0)},
        },
    }),
    'few_results': RdfCase(BLARG.aSearchFew, {
        BLARG.aSearchFew: {
            RDF.type: {TROVE.Cardsearch},
            TROVE.totalResultCount: {rdf.literal(3)},
            TROVE.searchResultPage: {
                rdf.sequence((
                    rdf.blanknode({
                        RDF.type: {TROVE.SearchResult},
                        TROVE.indexCard: {BLARG.aCard},
                    }),
                    rdf.blanknode({
                        RDF.type: {TROVE.SearchResult},
                        TROVE.indexCard: {BLARG.aCardd},
                    }),
                    rdf.blanknode({
                        RDF.type: {TROVE.SearchResult},
                        TROVE.indexCard: {BLARG.aCarddd},
                    }),
                )),
            },
        },
        BLARG.aCard: {
            RDF.type: {TROVE.Indexcard, DCAT.CatalogRecord},
            FOAF.primaryTopic: {BLARG.anItem},
            TROVE.focusIdentifier: {rdf.literal(BLARG.anItem)},
            DCTERMS.issued: {rdf.literal(datetime.date(2024, 1, 1))},
            DCTERMS.modified: {rdf.literal(datetime.date(2024, 1, 1))},
            TROVE.resourceMetadata: {rdf.literal(
                json.dumps({'@id': BLARG.anItem, 'title': 'an item, yes'}),
                datatype_iris=RDF.JSON,
            )},
        },
        BLARG.aCardd: {
            RDF.type: {TROVE.Indexcard, DCAT.CatalogRecord},
            FOAF.primaryTopic: {BLARG.anItemm},
            TROVE.focusIdentifier: {rdf.literal(BLARG.anItemm)},
            DCTERMS.issued: {rdf.literal(datetime.date(2024, 2, 2))},
            DCTERMS.modified: {rdf.literal(datetime.date(2024, 2, 2))},
            TROVE.resourceMetadata: {rdf.literal(
                json.dumps({'@id': BLARG.anItemm, 'title': 'an itemm, yes'}),
                datatype_iris=RDF.JSON,
            )},
        },
        BLARG.aCarddd: {
            RDF.type: {TROVE.Indexcard, DCAT.CatalogRecord},
            FOAF.primaryTopic: {BLARG.anItemmm},
            TROVE.focusIdentifier: {rdf.literal(BLARG.anItemmm)},
            DCTERMS.issued: {rdf.literal(datetime.date(2024, 3, 3))},
            DCTERMS.modified: {rdf.literal(datetime.date(2024, 3, 3))},
            TROVE.resourceMetadata: {rdf.literal(
                json.dumps({'@id': BLARG.anItemmm, 'title': 'an itemmm, yes'}),
                datatype_iris=RDF.JSON,
            )},
        },
    }),
}
