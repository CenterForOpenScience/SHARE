import json

from trove.derive.sharev2_elastic import ShareV2ElasticDeriver

from ._base import BaseIndexcardDeriverTest, SHOULD_SKIP


class TestShareV2ElasticDeriver(BaseIndexcardDeriverTest):
    maxDiff = None
    deriver_class = ShareV2ElasticDeriver

    def assert_derived_texts_equal(self, expected, actual):
        _actual = json.loads(actual)
        if expected is None:
            print(f'actual:\n{actual}')
        else:
            self.assertEqual(expected, _actual)

    expected_outputs = {
        'blarg-item': SHOULD_SKIP,
        'blarg-project': {
            "date": "2024-02-14",
            "date_created": "2345-01-01T00:00:00",
            "date_modified": "2345-02-02T00:00:00",
            "date_published": "2024-02-14",
            "id": "--suid_id--",
            "indexcard_id": "--indexcard-id--",
            "lists": {
                "contributors": [
                    {
                        "relation": "http://purl.org/dc/terms/creator"
                    }
                ]
            },
            "osf_related_resource_types": {
                "analytic_code": False,
                "data": False,
                "materials": False,
                "papers": False,
                "supplements": False
            },
            "rawdatum_id": "--rawdatum-id--",
            "retracted": False,
            "source_config": "--sourceconfig-label--",
            "source_unique_id": "--sourceunique-id--",
            "sources": [
                "--source-title--"
            ],
            "title": "title",
            "type": "project",
            "types": ["project"],
            "withdrawn": False
        },
        'sharev2-with-subjects': {
            "contributors": [
                "Some Rando"
            ],
            "date": "2019-01-23",
            "date_created": "2345-01-01T00:00:00",
            "date_modified": "2345-02-02T00:00:00",
            "date_published": "2019-01-23",
            "date_updated": "2019-01-23",
            "id": "--suid_id--",
            "identifiers": [
                "http://osf.example/chair/"
            ],
            "indexcard_id": "--indexcard-id--",
            "lists": {
                "contributors": [
                    {
                        "cited_as": "Some Rando",
                        "identifiers": [
                            "http://osf.example/rando/",
                            "mailto:rando@example.com"
                        ],
                        "name": "Some Rando",
                        "relation": "http://purl.org/dc/terms/creator",
                        "type": "person",
                        "types": [
                            "agent",
                            "person",
                        ]
                    }
                ],
                "lineage": [
                    {
                        "identifiers": [
                            "http://osf.example/mdept/"
                        ],
                        "title": "Miscellaneous department",
                        "type": "registration",
                        "types": [
                            "creative work",
                            "publication",
                            "registration",
                        ]
                    },
                    {
                        "identifiers": [
                            "http://osf.example/vroom/"
                        ],
                        "title": "Various room",
                        "type": "registration",
                        "types": [
                            "creative work",
                            "publication",
                            "registration",
                        ]
                    }
                ]
            },
            "osf_related_resource_types": {
                "analytic_code": False,
                "data": False,
                "materials": False,
                "papers": False,
                "supplements": False
            },
            "rawdatum_id": "--rawdatum-id--",
            "retracted": False,
            "source_config": "--sourceconfig-label--",
            "source_unique_id": "--sourceunique-id--",
            "sources": [
                "--source-title--"
            ],
            "title": "Assorted chair",
            "type": "registration",
            "types": [
                "creative work",
                "publication",
                "registration",
            ],
            "withdrawn": False
        },
        'osfmap-registration': {
            "contributors": ["JW"],
            "date": "2021-10-18",
            "date_created": "2345-01-01T00:00:00",
            "date_modified": "2345-02-02T00:00:00",
            "date_published": "2021-10-18",
            "date_updated": "2021-10-18",
            "description": "This registration tree is intended to demonstrate linkages between the OSF view of a Registration and the Internet Archive view",
            "hosts": ["OSF"],
            "id": "--suid_id--",
            "identifiers": [
                "https://doi.example/10.17605/OSF.IO/2C4ST",
                "https://osf.example/2c4st",
            ],
            "indexcard_id": "--indexcard-id--",
            "lists": {
                "contributors": [
                    {
                        "cited_as": "JW",
                        "identifiers": [
                            "https://osf.example/bhcjn"
                        ],
                        "name": "JW",
                        "relation": "http://purl.org/dc/terms/creator"
                    }
                ],
                "hosts": [
                    {
                        "cited_as": "OSF",
                        "identifiers": [
                            "https://osf.example"
                        ],
                        "name": "OSF",
                        "relation": "http://www.w3.org/ns/dcat#accessService"
                    }
                ],
                "publishers": [
                    {
                        "cited_as": "OSF Registries",
                        "identifiers": [
                            "https://osf.example/",
                            "https://osf.io/registries/osf"
                        ],
                        "name": "OSF Registries",
                        "relation": "http://purl.org/dc/terms/publisher"
                    }
                ]
            },
            "osf_related_resource_types": {
                "analytic_code": False,
                "data": False,
                "materials": False,
                "papers": False,
                "supplements": False
            },
            "publishers": [
                "OSF Registries"
            ],
            "rawdatum_id": "--rawdatum-id--",
            "retracted": False,
            "source_config": "--sourceconfig-label--",
            "source_unique_id": "--sourceunique-id--",
            "sources": ["--source-title--"],
            "subjects": ["bepress|Education"],
            "tags": [
                "Demo",
                "IA",
                "IMLS",
                "OSF",
            ],
            "title": "IA/IMLS Demo",
            "type": "registration",
            "types": [
                "registration"
            ],
            "withdrawn": False
        },
    }
