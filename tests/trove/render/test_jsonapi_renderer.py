import json
from unittest import mock

from trove.render.jsonapi import RdfJsonapiRenderer
from trove.render.rendering import SimpleRendering
from trove.vocab.namespaces import BLARG
from . import _base


def _jsonapi_item_sortkey(jsonapi_item: dict):
    return (jsonapi_item.get('type'), jsonapi_item.get('id'))


class _BaseJsonapiRendererTest(_base.TroveJsonRendererTests):
    renderer_class = RdfJsonapiRenderer

    def setUp(self):
        super().setUp()
        self.enterContext(
            mock.patch('trove.render.jsonapi.time.time_ns', return_value=112358)
        )

    def _get_rendered_output(self, rendering):
        _json = super()._get_rendered_output(rendering)
        _included = _json.get('included')
        if _included:
            # order of includes does not matter
            _included.sort(key=_jsonapi_item_sortkey)
        return _json


class TestJsonapiRenderer(_BaseJsonapiRendererTest):
    expected_outputs = {
        'simple_card': SimpleRendering(
            mediatype='application/vnd.api+json',
            rendered_content=json.dumps({
                "data": {
                    "id": "blarg:aCard",
                    "type": "index-card",
                    "attributes": {
                        "resourceIdentifier": [
                            BLARG.anItem
                        ],
                        "resourceMetadata": {
                            "@id": BLARG.anItem,
                            "title": "an item, yes"
                        }
                    },
                    "links": {
                        "self": BLARG.aCard,
                    },
                    "meta": {
                        "foaf:primaryTopic": [
                            {"@id": "blarg:anItem"},
                        ],
                        "dcterms:issued": [
                            "2024-01-01"
                        ],
                        "dcterms:modified": [
                            "2024-01-01"
                        ]
                    },
                }
            }),
        ),
        'various_types': SimpleRendering(
            mediatype='application/vnd.api+json',
            rendered_content=json.dumps({
                "data": {
                    "id": "blarg:aSubject",
                    "type": "blarg:aType",
                    "meta": {
                        "blarg:hasIri": [{"@id": "blarg:anIri"}],
                        "blarg:hasRdfStringLiteral": ["an rdf:string literal"],
                        "blarg:hasRdfLangStringLiteral": ['a rdf:langString literal'],
                        "blarg:hasIntegerLiteral": [17],
                        "blarg:hasDateLiteral": ["2024-01-01"],
                        "blarg:hasStrangeLiteral": ['a literal of strange datatype'],
                    },
                    "links": {"self": BLARG.aSubject},
                }
            }),
        ),
    }


class TestJsonapiSearchRenderer(_BaseJsonapiRendererTest, _base.TrovesearchJsonRendererTests):
    expected_outputs = {
        'no_results': SimpleRendering(
            mediatype='application/vnd.api+json',
            rendered_content=json.dumps({
                "data": {
                    "id": "blarg:aSearch",
                    "type": "index-card-search",
                    "attributes": {
                        "totalResultCount": 0,
                    },
                    "links": {
                        "self": BLARG.aSearch,
                    }
                }
            }),
        ),
        'few_results': SimpleRendering(
            mediatype='application/vnd.api+json',
            rendered_content=json.dumps({
                "data": {
                    "id": "blarg:aSearchFew",
                    "type": "index-card-search",
                    "attributes": {
                        "totalResultCount": 3
                    },
                    "relationships": {
                        "searchResultPage": {
                            "data": [
                                {
                                    "id": "112358-0",
                                    "type": "search-result"
                                },
                                {
                                    "id": "112358-1",
                                    "type": "search-result"
                                },
                                {
                                    "id": "112358-2",
                                    "type": "search-result"
                                }
                            ]
                        }
                    },
                    "links": {
                        "self": BLARG.aSearchFew
                    }
                },
                "included": [
                    {
                        "id": "112358-0",
                        "type": "search-result",
                        "relationships": {
                            "indexCard": {
                                "data": {
                                    "id": "blarg:aCard",
                                    "type": "index-card"
                                }
                            }
                        }
                    },
                    {
                        "id": "112358-1",
                        "type": "search-result",
                        "relationships": {
                            "indexCard": {
                                "data": {
                                    "id": "blarg:aCardd",
                                    "type": "index-card"
                                }
                            }
                        }
                    },
                    {
                        "id": "112358-2",
                        "type": "search-result",
                        "relationships": {
                            "indexCard": {
                                "data": {
                                    "id": "blarg:aCarddd",
                                    "type": "index-card"
                                }
                            }
                        }
                    },
                    {
                        "id": "blarg:aCard",
                        "type": "index-card",
                        "meta": {
                            "foaf:primaryTopic": [
                                {"@id": "blarg:anItem"},
                            ],
                            "dcterms:issued": [
                                "2024-01-01"
                            ],
                            "dcterms:modified": [
                                "2024-01-01"
                            ]
                        },
                        "attributes": {
                            "resourceIdentifier": [
                                BLARG.anItem
                            ],
                            "resourceMetadata": {
                                "@id": BLARG.anItem,
                                "title": "an item, yes"
                            }
                        },
                        "links": {
                            "self": BLARG.aCard
                        }
                    },
                    {
                        "id": "blarg:aCarddd",
                        "type": "index-card",
                        "meta": {
                            "foaf:primaryTopic": [
                                {"@id": "blarg:anItemmm"},
                            ],
                            "dcterms:issued": [
                                "2024-03-03"
                            ],
                            "dcterms:modified": [
                                "2024-03-03"
                            ]
                        },
                        "attributes": {
                            "resourceIdentifier": [
                                BLARG.anItemmm
                            ],
                            "resourceMetadata": {
                                "@id": BLARG.anItemmm,
                                "title": "an itemmm, yes"
                            }
                        },
                        "links": {
                            "self": BLARG.aCarddd
                        }
                    },
                    {
                        "id": "blarg:aCardd",
                        "type": "index-card",
                        "meta": {
                            "foaf:primaryTopic": [
                                {"@id": "blarg:anItemm"},
                            ],
                            "dcterms:issued": [
                                "2024-02-02"
                            ],
                            "dcterms:modified": [
                                "2024-02-02"
                            ]
                        },
                        "attributes": {
                            "resourceIdentifier": [
                                BLARG.anItemm
                            ],
                            "resourceMetadata": {
                                "@id": BLARG.anItemm,
                                "title": "an itemm, yes"
                            }
                        },
                        "links": {
                            "self": BLARG.aCardd
                        }
                    }
                ],
            }),
        ),
    }
