import json

from trove.render.jsonld import RdfJsonldRenderer
from trove.render._rendering import SimpleRendering
from ._inputs import BLARG
from . import _base


class TestJsonldRenderer(_base.TroveJsonRendererTests):
    renderer_class = RdfJsonldRenderer

    expected_outputs = {
        'simple_card': SimpleRendering(
            mediatype='application/ld+json',
            rendered_content=json.dumps({
                "@id": BLARG.aCard,
                "dcterms:issued": [
                    {
                        "@type": "xsd:date",
                        "@value": "2024-01-01"
                    }
                ],
                "dcterms:modified": [
                    {
                        "@type": "xsd:date",
                        "@value": "2024-01-01"
                    }
                ],
                "foaf:primaryTopic": [
                    BLARG.anItem
                ],
                "rdf:type": [
                    "trove:Indexcard",
                    "dcat:CatalogRecord"
                ],
                "trove:focusIdentifier": [
                    {
                        "@value": BLARG.anItem
                    }
                ],
                "trove:resourceMetadata": {
                    "@id": BLARG.anItem,
                    "title": "an item, yes"
                }
            }),
        ),
        'various_types': SimpleRendering(
            mediatype='application/ld+json',
            rendered_content=json.dumps({
                "@id": BLARG.aSubject,
                BLARG.hasDateLiteral: [
                    {
                        "@type": "xsd:date",
                        "@value": "2024-01-01"
                    }
                ],
                BLARG.hasIntegerLiteral: [
                    {
                        "@type": "xsd:integer",
                        "@value": "17"
                    }
                ],
                BLARG.hasIri: [
                    BLARG.anIri
                ],
                BLARG.hasRdfLangStringLiteral: [
                    {
                        "@language": "en",
                        "@value": "a rdf:langString literal"
                    }
                ],
                BLARG.hasRdfStringLiteral: [
                    {
                        "@value": "an rdf:string literal"
                    }
                ],
                BLARG.hasStrangeLiteral: [
                    {
                        "@type": BLARG.aStrangeDatatype,
                        "@value": "a literal of strange datatype"
                    }
                ],
                "rdf:type": [BLARG.aType],
            }),
        ),
    }


class TestJsonldSearchRenderer(_base.TrovesearchJsonRendererTests):
    renderer_class = RdfJsonldRenderer

    expected_outputs = {
        'no_results': SimpleRendering(
            mediatype='application/ld+json',
            rendered_content=json.dumps({
                "@id": BLARG.aSearch,
                "rdf:type": [
                    "trove:Cardsearch"
                ],
                "trove:totalResultCount": {
                    "@type": "xsd:integer",
                    "@value": "0"
                }
            }),
        ),
        'few_results': SimpleRendering(
            mediatype='application/ld+json',
            rendered_content=json.dumps({
                "@id": BLARG.aSearchFew,
                "rdf:type": [
                    "trove:Cardsearch"
                ],
                "trove:totalResultCount": {
                    "@type": "xsd:integer",
                    "@value": "3"
                },
                "trove:searchResultPage": [
                    {
                        "@list": [
                            {
                                "rdf:type": [
                                    "trove:SearchResult"
                                ],
                                "trove:indexCard": {
                                    "@id": BLARG.aCard,
                                    "dcterms:issued": [
                                        {
                                            "@type": "xsd:date",
                                            "@value": "2024-01-01"
                                        }
                                    ],
                                    "dcterms:modified": [
                                        {
                                            "@type": "xsd:date",
                                            "@value": "2024-01-01"
                                        }
                                    ],
                                    "foaf:primaryTopic": [
                                        BLARG.anItem
                                    ],
                                    "rdf:type": [
                                        "trove:Indexcard",
                                        "dcat:CatalogRecord"
                                    ],
                                    "trove:focusIdentifier": [
                                        {
                                            "@value": BLARG.anItem
                                        }
                                    ],
                                    "trove:resourceMetadata": {
                                        "@id": BLARG.anItem,
                                        "title": "an item, yes"
                                    }
                                }
                            },
                            {
                                "rdf:type": [
                                    "trove:SearchResult"
                                ],
                                "trove:indexCard": {
                                    "@id": BLARG.aCardd,
                                    "dcterms:issued": [
                                        {
                                            "@type": "xsd:date",
                                            "@value": "2024-02-02"
                                        }
                                    ],
                                    "dcterms:modified": [
                                        {
                                            "@type": "xsd:date",
                                            "@value": "2024-02-02"
                                        }
                                    ],
                                    "foaf:primaryTopic": [
                                        BLARG.anItemm
                                    ],
                                    "rdf:type": [
                                        "trove:Indexcard",
                                        "dcat:CatalogRecord"
                                    ],
                                    "trove:focusIdentifier": [
                                        {
                                            "@value": BLARG.anItemm
                                        }
                                    ],
                                    "trove:resourceMetadata": {
                                        "@id": BLARG.anItemm,
                                        "title": "an itemm, yes"
                                    }
                                }
                            },
                            {
                                "rdf:type": [
                                    "trove:SearchResult"
                                ],
                                "trove:indexCard": {
                                    "@id": BLARG.aCarddd,
                                    "dcterms:issued": [
                                        {
                                            "@type": "xsd:date",
                                            "@value": "2024-03-03"
                                        }
                                    ],
                                    "dcterms:modified": [
                                        {
                                            "@type": "xsd:date",
                                            "@value": "2024-03-03"
                                        }
                                    ],
                                    "foaf:primaryTopic": [
                                        BLARG.anItemmm
                                    ],
                                    "rdf:type": [
                                        "trove:Indexcard",
                                        "dcat:CatalogRecord"
                                    ],
                                    "trove:focusIdentifier": [
                                        {
                                            "@value": BLARG.anItemmm
                                        }
                                    ],
                                    "trove:resourceMetadata": {
                                        "@id": BLARG.anItemmm,
                                        "title": "an itemmm, yes"
                                    }
                                }
                            }
                        ]
                    }
                ],
            }),
        ),
    }
