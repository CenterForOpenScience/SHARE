import json

from trove.render.simple_json import TrovesearchSimpleJsonRenderer
from trove.render._rendering import SimpleRendering
from . import _base


# note: trovesearch only -- this renderer doesn't do arbitrary rdf

class TestSimpleJsonRenderer(_base.TrovesearchJsonRendererTests):
    renderer_class = TrovesearchSimpleJsonRenderer
    expected_outputs = {
        'no_results': SimpleRendering(
            mediatype='application/json',
            rendered_content=json.dumps({
                "data": [],
                "links": {},
                "meta": {
                    "total": 0
                }
            }),
        ),
        'few_results': SimpleRendering(
            mediatype='application/json',
            rendered_content=json.dumps({
                "data": [
                    {
                        "@id": "http://blarg.example/vocab/anItem",
                        "title": "an item, yes",
                        "foaf:primaryTopicOf": [
                            {
                                "@id": "http://blarg.example/vocab/aCard"
                            }
                        ]
                    },
                    {
                        "@id": "http://blarg.example/vocab/anItemm",
                        "title": "an itemm, yes",
                        "foaf:primaryTopicOf": [
                            {
                                "@id": "http://blarg.example/vocab/aCardd"
                            }
                        ]
                    },
                    {
                        "@id": "http://blarg.example/vocab/anItemmm",
                        "title": "an itemmm, yes",
                        "foaf:primaryTopicOf": [
                            {
                                "@id": "http://blarg.example/vocab/aCarddd"
                            }
                        ]
                    }
                ],
                "links": {},
                "meta": {
                    "total": 3
                }
            }),
        ),
    }
