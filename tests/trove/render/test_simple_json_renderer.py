import json

from trove.render.simple_json import TrovesearchSimpleJsonRenderer
from trove.render._rendering import SimpleRendering
from trove.vocab.namespaces import BLARG
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
                        "@id": BLARG.anItem,
                        "title": "an item, yes",
                        "foaf:primaryTopicOf": [
                            {
                                "@id": BLARG.aCard
                            }
                        ]
                    },
                    {
                        "@id": BLARG.anItemm,
                        "title": "an itemm, yes",
                        "foaf:primaryTopicOf": [
                            {
                                "@id": BLARG.aCardd
                            }
                        ]
                    },
                    {
                        "@id": BLARG.anItemmm,
                        "title": "an itemmm, yes",
                        "foaf:primaryTopicOf": [
                            {
                                "@id": BLARG.aCarddd
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
