import json

from trove.render.simple_json import TrovesearchSimpleJsonRenderer
from trove.render.rendering import EntireRendering
from trove.vocab.namespaces import BLARG
from . import _base


# note: trovesearch only -- this renderer doesn't do arbitrary rdf

class TestSimpleJsonRenderer(_base.TrovesearchJsonRendererTests):
    renderer_class = TrovesearchSimpleJsonRenderer
    expected_outputs = {
        'no_results': EntireRendering(
            mediatype='application/json',
            entire_content=json.dumps({
                "data": [],
                "links": {},
                "meta": {
                    "total": 0
                }
            }),
        ),
        'few_results': EntireRendering(
            mediatype='application/json',
            entire_content=json.dumps({
                "data": [
                    {
                        "@id": BLARG.anItem,
                        "title": [{"@value": "an item, yes"}],
                        "foaf:isPrimaryTopicOf": [{"@id": BLARG.aCard}]
                    },
                    {
                        "@id": BLARG.anItemm,
                        "title": [{"@value": "an itemm, yes"}],
                        "foaf:isPrimaryTopicOf": [{"@id": BLARG.aCardd}]
                    },
                    {
                        '@id': BLARG.anItemmm,
                        "sameAs": [
                            {"@id": "https://doi.example/13.0/anItemmm"}
                        ],
                        'title': [{'@value': 'an itemmm, yes'}],
                        "creator": [
                            {
                                "@id": BLARG.aPerson,
                                "resourceType": [
                                    {"@id": "Agent"},
                                    {"@id": "Person"}
                                ],
                                "identifier": [
                                    {"@value": BLARG.aPerson}
                                ],
                                "name": [
                                    {"@value": "a person indeed"}
                                ]
                            }
                        ],
                        "dateCreated": [
                            {"@value": "2001-02-03"}
                        ],
                        "foaf:isPrimaryTopicOf": [{"@id": BLARG.aCarddd}]
                    }
                ],
                "links": {},
                "meta": {
                    "total": 3
                }
            }),
        ),
    }
