import json

from trove.render.jsonld import RdfJsonldRenderer
from trove.render._rendering import SimpleRendering
from . import _base


class TestJsonldRenderer(_base.TroveJsonRendererTests):
    renderer_class = RdfJsonldRenderer

    expected_outputs = {
        'simple_card': SimpleRendering(
            mediatype='application/ld+json',
            rendered_content=json.dumps({
                "@id": "http://blarg.example/vocab/aCard",
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
                    "http://blarg.example/vocab/anItem"
                ],
                "rdf:type": [
                    "trove:Indexcard",
                    "dcat:CatalogRecord"
                ],
                "trove:focusIdentifier": [
                    {
                        "@value": "http://blarg.example/vocab/anItem"
                    }
                ],
                "trove:resourceMetadata": {
                    "@id": "http://blarg.example/vocab/anItem",
                    "title": "an item, yes"
                }
            }),
        ),
    }


class TestJsonldSearchRenderer(_base.TrovesearchJsonRendererTests):
    renderer_class = RdfJsonldRenderer

    expected_outputs = {
        'no_results': SimpleRendering(
            mediatype='application/ld+json',
            rendered_content=json.dumps({
                "@id": "http://blarg.example/vocab/aSearch",
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
                "@id": "http://blarg.example/vocab/aSearchFew",
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
                                    "@id": "http://blarg.example/vocab/aCard",
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
                                        "http://blarg.example/vocab/anItem"
                                    ],
                                    "rdf:type": [
                                        "trove:Indexcard",
                                        "dcat:CatalogRecord"
                                    ],
                                    "trove:focusIdentifier": [
                                        {
                                            "@value": "http://blarg.example/vocab/anItem"
                                        }
                                    ],
                                    "trove:resourceMetadata": {
                                        "@id": "http://blarg.example/vocab/anItem",
                                        "title": "an item, yes"
                                    }
                                }
                            },
                            {
                                "rdf:type": [
                                    "trove:SearchResult"
                                ],
                                "trove:indexCard": {
                                    "@id": "http://blarg.example/vocab/aCardd",
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
                                        "http://blarg.example/vocab/anItemm"
                                    ],
                                    "rdf:type": [
                                        "trove:Indexcard",
                                        "dcat:CatalogRecord"
                                    ],
                                    "trove:focusIdentifier": [
                                        {
                                            "@value": "http://blarg.example/vocab/anItemm"
                                        }
                                    ],
                                    "trove:resourceMetadata": {
                                        "@id": "http://blarg.example/vocab/anItemm",
                                        "title": "an itemm, yes"
                                    }
                                }
                            },
                            {
                                "rdf:type": [
                                    "trove:SearchResult"
                                ],
                                "trove:indexCard": {
                                    "@id": "http://blarg.example/vocab/aCarddd",
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
                                        "http://blarg.example/vocab/anItemmm"
                                    ],
                                    "rdf:type": [
                                        "trove:Indexcard",
                                        "dcat:CatalogRecord"
                                    ],
                                    "trove:focusIdentifier": [
                                        {
                                            "@value": "http://blarg.example/vocab/anItemmm"
                                        }
                                    ],
                                    "trove:resourceMetadata": {
                                        "@id": "http://blarg.example/vocab/anItemmm",
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
