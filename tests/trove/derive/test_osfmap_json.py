import json
from trove.derive.osfmap_json import OsfmapJsonFullDeriver
from trove.derive.osfmap_json_mini import IndexcardJsonDeriver
from ._base import BaseIndexcardDeriverTest


class TestOsfmapJsonDeriver(BaseIndexcardDeriverTest):
    deriver_class = OsfmapJsonFullDeriver
    expected_outputs = {
        'blarg-item': {
            "@id": "blarg:my_item",
            "resourceType": [{"@id": "blarg:Item"}],
            "title": [{
                "@value": "title",
                "@language": "en"
            }],
            "creator": [{
                "@id": "blarg:me",
                "resourceType": [{"@id": "Person"}],
                "name": [{"@value": "me me"}]
            }],
            "dateCreated": [{"@value": "2024-02-14"}],
        },
        'blarg-project': {
            "@id": "blarg:my_project",
            "resourceType": [
                {"@id": "Project"},
                {"@id": "blarg:Item"},
            ],
            "title": [{
                "@value": "title",
                "@language": "en",
            }],
            "creator": [{
                "@id": "blarg:me",
                "resourceType": [{"@id": "Person"}],
                "name": [{"@value": "me me"}]
            }],
            "dateCreated": [{"@value": "2024-02-14"}],
        },
        'sharev2-with-subjects': {
            "@id": "http://osf.example/chair/",
            "resourceType": [
                {"@id": "sharev2:CreativeWork"},
                {"@id": "sharev2:Publication"},
                {"@id": "sharev2:Registration"},
            ],
            "conformsTo": [{"name": [{"@value": "Open-Ended Registration"}]}],
            "dateCreated": [
                {
                    "@value": "2019-01-23",
                    "@type": "xsd:date"
                }
            ],
            "creator": [
                {
                    "@id": "mailto:rando@example.com",
                    "resourceType": [
                        {"@id": "Person"},
                        {"@id": "sharev2:Agent"},
                        {"@id": "sharev2:Person"}
                    ],
                    "identifier": [
                        {"@value": "http://osf.example/rando/"},
                        {"@value": "mailto:rando@example.com"}
                    ],
                    "sameAs": [
                        {"@id": "http://osf.example/rando/"}
                    ],
                    "name": [
                        {"@value": "Some Rando"}
                    ],
                    "affiliation": [
                        {
                            "@id": "http://wassa.example",
                            "resourceType": [
                                {"@id": "Organization"},
                                {"@id": "sharev2:Agent"},
                                {"@id": "sharev2:Institution"},
                                {"@id": "sharev2:Organization"}
                            ],
                            "name": [
                                {"@value": "Wassamatter University"}
                            ]
                        }
                    ]
                }
            ],
            "date": [
                {
                    "@value": "2019-01-23",
                    "@type": "xsd:date"
                }
            ],
            "identifier": [
                {"@value": "http://osf.example/chair/"}
            ],
            "isPartOf": [
                {
                    "@id": "http://osf.example/vroom/",
                    "resourceType": [
                        {"@id": "sharev2:CreativeWork"},
                        {"@id": "sharev2:Publication"},
                        {"@id": "sharev2:Registration"}
                    ],
                    "identifier": [
                        {"@value": "http://osf.example/vroom/"}
                    ],
                    "isPartOf": [
                        {
                            "@id": "http://osf.example/mdept/",
                            "resourceType": [
                                {"@id": "sharev2:CreativeWork"},
                                {"@id": "sharev2:Publication"},
                                {"@id": "sharev2:Registration"}
                            ],
                            "identifier": [
                                {"@value": "http://osf.example/mdept/"}
                            ],
                            "title": [
                                {"@value": "Miscellaneous department"}
                            ]
                        }
                    ],
                    "title": [
                        {"@value": "Various room"}
                    ]
                }
            ],
            "subject": [
                {"@value": "Architecture"},
                {"@value": "Biology"},
                {"@value": "Custom biologyyyy"},
                {"@value": "bepress|Architecture"},
                {"@value": "bepress|Life Sciences|Biology"},
                {"@value": "foo|Custom life sciencesssss|Custom biologyyyy"}
            ],
            "title": [
                {"@value": "Assorted chair"}
            ],
            "affiliation": [
                {
                    "@id": "http://wassa.example",
                    "resourceType": [
                        {"@id": "Organization"},
                        {"@id": "sharev2:Agent"},
                        {"@id": "sharev2:Institution"},
                        {"@id": "sharev2:Organization"}
                    ],
                    "name": [
                        {"@value": "Wassamatter University"}
                    ]
                }
            ]
        },
        'osfmap-registration': {
            "@id": "https://osf.example/2c4st",
            "resourceType": [
                {"@id": "Registration"}
            ],
            "conformsTo": [
                {
                    "@id": "https://api.osf.example/v2/schemas/registrations/564d31db8c5e4a7c9694b2be/",
                    "title": [
                        {"@value": "Open-Ended Registration"}
                    ]
                }
            ],
            "dateCreated": [
                {"@value": "2021-10-18"}
            ],
            "creator": [
                {
                    "@id": "https://osf.example/bhcjn",
                    "resourceType": [
                        {"@id": "Agent"},
                        {"@id": "Person"}
                    ],
                    "identifier": [
                        {"@value": "https://osf.example/bhcjn"}
                    ],
                    "name": [
                        {"@value": "JW"}
                    ],
                    "affiliation": [
                        {
                            "@id": "https://ror.example/05d5mza29",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://ror.example/05d5mza29"}
                            ],
                            "name": [
                                {"@value": "Center For Open Science"}
                            ]
                        }
                    ]
                }
            ],
            'qualifiedAttribution': [{
                'agent': [{'@id': 'https://osf.example/bhcjn'}],
                'hadRole': [{'@id': 'osf:admin-contributor'}],
            }],
            "dateCopyrighted": [
                {"@value": "2021"}
            ],
            "description": [
                {
                    "@value": "This registration tree is intended to demonstrate linkages between the OSF view of a Registration and the Internet Archive view"}
            ],
            "hasPart": [
                {
                    "@id": "https://osf.example/482n5",
                    "resourceType": [
                        {"@id": "RegistrationComponent"}
                    ],
                    "dateCreated": [
                        {"@value": "2021-10-18"}
                    ],
                    "creator": [
                        {
                            "@id": "https://osf.example/bhcjn",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Person"}
                            ],
                            "identifier": [
                                {"@value": "https://osf.example/bhcjn"}
                            ],
                            "name": [
                                {"@value": "JW"}
                            ],
                            "affiliation": [
                                {
                                    "@id": "https://ror.example/05d5mza29",
                                    "resourceType": [
                                        {"@id": "Agent"},
                                        {"@id": "Organization"}
                                    ],
                                    "identifier": [
                                        {"@value": "https://ror.example/05d5mza29"}
                                    ],
                                    "name": [
                                        {"@value": "Center For Open Science"}
                                    ]
                                }
                            ]
                        }
                    ],
                    "dateCopyrighted": [
                        {"@value": "2021"}
                    ],
                    "identifier": [
                        {"@value": "https://doi.example/10.17605/OSF.IO/482N5"},
                        {"@value": "https://osf.example/482n5"}
                    ],
                    "publisher": [
                        {
                            "@id": "https://osf.example/registries/osf",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://osf.example/"},
                                {"@value": "https://osf.io/registries/osf"}
                            ],
                            "name": [
                                {"@value": "OSF Registries"}
                            ]
                        }
                    ],
                    "rights": [
                        {
                            "@id": "https://creativecommons.example/licenses/by/4.0/legalcode",
                            "identifier": [
                                {"@value": "https://creativecommons.example/licenses/by/4.0/legalcode"}
                            ],
                            "name": [
                                {"@value": "CC-By Attribution 4.0 International"}
                            ]
                        }
                    ],
                    "title": [
                        {"@value": "IA/IMLS Demo: Child Component"}
                    ],
                    "sameAs": [
                        {"@id": "https://doi.example/10.17605/OSF.IO/482N5"}
                    ],
                    "affiliation": [
                        {
                            "@id": "https://ror.example/05d5mza29",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://ror.example/05d5mza29"}
                            ],
                            "name": [
                                {"@value": "Center For Open Science"}
                            ]
                        }
                    ]
                }
            ],
            "identifier": [
                {"@value": "https://doi.example/10.17605/OSF.IO/2C4ST"},
                {"@value": "https://osf.example/2c4st"}
            ],
            "isVersionOf": [
                {
                    "@id": "https://osf.example/hnm67",
                    "resourceType": [
                        {"@id": "Project"}
                    ],
                    "dateCreated": [
                        {"@value": "2021-10-18"}
                    ],
                    "creator": [
                        {
                            "@id": "https://osf.example/bhcjn",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Person"}
                            ],
                            "identifier": [
                                {"@value": "https://osf.example/bhcjn"}
                            ],
                            "name": [
                                {"@value": "JW"}
                            ],
                            "affiliation": [
                                {
                                    "@id": "https://ror.example/05d5mza29",
                                    "resourceType": [
                                        {"@id": "Agent"},
                                        {"@id": "Organization"}
                                    ],
                                    "identifier": [
                                        {"@value": "https://ror.example/05d5mza29"}
                                    ],
                                    "name": [
                                        {"@value": "Center For Open Science"}
                                    ]
                                }
                            ]
                        }
                    ],
                    "identifier": [
                        {"@value": "https://osf.example/hnm67"}
                    ],
                    "publisher": [
                        {
                            "@id": "https://osf.example",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://osf.example"}
                            ],
                            "name": [
                                {"@value": "OSF"}
                            ]
                        }
                    ],
                    "title": [
                        {"@value": "IA/IMLS Demo"}
                    ],
                    "affiliation": [
                        {
                            "@id": "https://ror.example/05d5mza29",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://ror.example/05d5mza29"}
                            ],
                            "name": [
                                {"@value": "Center For Open Science"}
                            ]
                        }
                    ]
                }
            ],
            "dateModified": [
                {"@value": "2021-10-18"}
            ],
            "publisher": [
                {
                    "@id": "https://osf.example/registries/osf",
                    "resourceType": [
                        {"@id": "Agent"},
                        {"@id": "Organization"}
                    ],
                    "identifier": [
                        {"@value": "https://osf.example/"},
                        {"@value": "https://osf.io/registries/osf"}
                    ],
                    "name": [
                        {"@value": "OSF Registries"}
                    ]
                }
            ],
            "rights": [
                {
                    "@id": "https://creativecommons.example/licenses/by-nc-nd/4.0/legalcode",
                    "identifier": [
                        {"@value": "https://creativecommons.example/licenses/by-nc-nd/4.0/legalcode"}
                    ],
                    "name": [
                        {"@value": "CC-By Attribution-NonCommercial-NoDerivatives 4.0 International"}
                    ]
                }
            ],
            "subject": [
                {
                    "@id": "https://api.osf.example/v2/subjects/584240da54be81056cecaae5",
                    "resourceType": [
                        {"@id": "Concept"}
                    ],
                    "inScheme": [
                        {
                            "@id": "https://bepress.com/reference_guide_dc/disciplines/",
                            "resourceType": [
                                {"@id": "Concept:Scheme"}
                            ],
                            "title": [
                                {"@value": "bepress Digital Commons Three-Tiered Taxonomy"}
                            ]
                        }
                    ],
                    "prefLabel": [
                        {"@value": "Education"}
                    ]
                }
            ],
            "title": [
                {"@value": "IA/IMLS Demo"}
            ],
            "sameAs": [
                {"@id": "https://doi.example/10.17605/OSF.IO/2C4ST"}
            ],
            "accessService": [
                {
                    "@id": "https://osf.example",
                    "resourceType": [
                        {"@id": "Agent"},
                        {"@id": "Organization"}
                    ],
                    "identifier": [
                        {"@value": "https://osf.example"}
                    ],
                    "name": [
                        {"@value": "OSF"}
                    ]
                }
            ],
            "affiliation": [
                {
                    "@id": "https://ror.example/05d5mza29",
                    "resourceType": [
                        {"@id": "Agent"},
                        {"@id": "Organization"}
                    ],
                    "identifier": [
                        {"@value": "https://ror.example/05d5mza29"}
                    ],
                    "name": [
                        {"@value": "Center For Open Science"}
                    ]
                }
            ],
            "archivedAt": [
                {"@id": "https://archive.example/details/osf-registrations-2c4st-v1"}
            ],
            "osf:contains": [
                {
                    "@id": "https://osf.example/2ph9b",
                    "resourceType": [
                        {"@id": "File"}
                    ],
                    "dateCreated": [
                        {"@value": "2021-10-18"}
                    ],
                    "identifier": [
                        {"@value": "https://osf.example/2ph9b"}
                    ],
                    "dateModified": [
                        {"@value": "2021-10-18"}
                    ],
                    "fileName": [
                        {"@value": "test_file.txt"}
                    ],
                    "filePath": [
                        {"@value": "/Archive of OSF Storage/test_file.txt"}
                    ],
                    "isContainedBy": [
                        {"@id": "https://osf.example/2c4st"}
                    ]
                }
            ],
            "hostingInstitution": [
                {
                    "@id": "https://cos.example/",
                    "resourceType": [
                        {"@id": "Agent"},
                        {"@id": "Organization"}
                    ],
                    "identifier": [
                        {"@value": "https://cos.example/"},
                        {"@value": "https://ror.example/05d5mza29"}
                    ],
                    "sameAs": [
                        {
                            "@id": "https://ror.example/05d5mza29",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://ror.example/05d5mza29"}
                            ],
                            "name": [
                                {"@value": "Center For Open Science"}
                            ]
                        }
                    ],
                    "name": [
                        {"@value": "Center for Open Science"}
                    ]
                }
            ],
            "keyword": [
                {"@value": "Demo"},
                {"@value": "IA"},
                {"@value": "IMLS"},
                {"@value": "OSF"}
            ]
        }
    }

    def assert_outputs_equal(self, expected, actual):
        self.assertEqual(expected, json.loads(actual))


class TestIndexcardJsonDeriver(BaseIndexcardDeriverTest):
    deriver_class = IndexcardJsonDeriver
    expected_outputs = {
        'blarg-item': {
            "@id": "blarg:my_item",
            "resourceType": [{"@id": "blarg:Item"}],
            "title": [{
                "@value": "title",
                "@language": "en"
            }],
            "creator": [{
                "@id": "blarg:me",
                "resourceType": [{"@id": "Person"}],
                "name": [{"@value": "me me"}]
            }],
            "dateCreated": [{"@value": "2024-02-14"}],
        },
        'blarg-project': {
            "@id": "blarg:my_project",
            "resourceType": [
                {"@id": "Project"},
                {"@id": "blarg:Item"},
            ],
            "title": [{
                "@value": "title",
                "@language": "en",
            }],
            "creator": [{
                "@id": "blarg:me",
                "resourceType": [{"@id": "Person"}],
                "name": [{"@value": "me me"}]
            }],
            "dateCreated": [{"@value": "2024-02-14"}],
        },
        'sharev2-with-subjects': {
            "@id": "http://osf.example/chair/",
            "resourceType": [
                {"@id": "sharev2:CreativeWork"},
                {"@id": "sharev2:Publication"},
                {"@id": "sharev2:Registration"},
            ],
            "conformsTo": [{"name": [{"@value": "Open-Ended Registration"}]}],
            "dateCreated": [
                {
                    "@value": "2019-01-23",
                    "@type": "xsd:date"
                }
            ],
            "creator": [
                {
                    "@id": "mailto:rando@example.com",
                    "resourceType": [
                        {"@id": "Person"},
                        {"@id": "sharev2:Agent"},
                        {"@id": "sharev2:Person"}
                    ],
                    "identifier": [
                        {"@value": "http://osf.example/rando/"},
                        {"@value": "mailto:rando@example.com"}
                    ],
                    "sameAs": [
                        {"@id": "http://osf.example/rando/"}
                    ],
                    "name": [
                        {"@value": "Some Rando"}
                    ],
                    "affiliation": [
                        {
                            "@id": "http://wassa.example",
                            "resourceType": [
                                {"@id": "Organization"},
                                {"@id": "sharev2:Agent"},
                                {"@id": "sharev2:Institution"},
                                {"@id": "sharev2:Organization"}
                            ],
                            "name": [
                                {"@value": "Wassamatter University"}
                            ]
                        }
                    ]
                }
            ],
            "date": [
                {
                    "@value": "2019-01-23",
                    "@type": "xsd:date"
                }
            ],
            "identifier": [
                {"@value": "http://osf.example/chair/"}
            ],
            "isPartOf": [
                {
                    "@id": "http://osf.example/vroom/",
                    "resourceType": [
                        {"@id": "sharev2:CreativeWork"},
                        {"@id": "sharev2:Publication"},
                        {"@id": "sharev2:Registration"}
                    ],
                    "identifier": [
                        {"@value": "http://osf.example/vroom/"}
                    ],
                    "isPartOf": [
                        {
                            "@id": "http://osf.example/mdept/",
                            "resourceType": [
                                {"@id": "sharev2:CreativeWork"},
                                {"@id": "sharev2:Publication"},
                                {"@id": "sharev2:Registration"}
                            ],
                            "identifier": [
                                {"@value": "http://osf.example/mdept/"}
                            ],
                            "title": [
                                {"@value": "Miscellaneous department"}
                            ]
                        }
                    ],
                    "title": [
                        {"@value": "Various room"}
                    ]
                }
            ],
            "subject": [
                {"@value": "Architecture"},
                {"@value": "Biology"},
                {"@value": "Custom biologyyyy"},
                {"@value": "bepress|Architecture"},
                {"@value": "bepress|Life Sciences|Biology"},
                {"@value": "foo|Custom life sciencesssss|Custom biologyyyy"}
            ],
            "title": [
                {"@value": "Assorted chair"}
            ],
            "affiliation": [
                {
                    "@id": "http://wassa.example",
                    "resourceType": [
                        {"@id": "Organization"},
                        {"@id": "sharev2:Agent"},
                        {"@id": "sharev2:Institution"},
                        {"@id": "sharev2:Organization"}
                    ],
                    "name": [
                        {"@value": "Wassamatter University"}
                    ]
                }
            ]
        },
        'osfmap-registration': {
            "@id": "https://osf.example/2c4st",
            "resourceType": [
                {"@id": "Registration"}
            ],
            "conformsTo": [
                {
                    "@id": "https://api.osf.example/v2/schemas/registrations/564d31db8c5e4a7c9694b2be/",
                    "title": [
                        {"@value": "Open-Ended Registration"}
                    ]
                }
            ],
            "dateCreated": [
                {"@value": "2021-10-18"}
            ],
            "creator": [
                {
                    "@id": "https://osf.example/bhcjn",
                    "resourceType": [
                        {"@id": "Agent"},
                        {"@id": "Person"}
                    ],
                    "identifier": [
                        {"@value": "https://osf.example/bhcjn"}
                    ],
                    "name": [
                        {"@value": "JW"}
                    ],
                    "affiliation": [
                        {
                            "@id": "https://ror.example/05d5mza29",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://ror.example/05d5mza29"}
                            ],
                            "name": [
                                {"@value": "Center For Open Science"}
                            ]
                        }
                    ]
                }
            ],
            "dateCopyrighted": [
                {"@value": "2021"}
            ],
            "description": [
                {
                    "@value": "This registration tree is intended to demonstrate linkages between the OSF view of a Registration and the Internet Archive view"}
            ],
            "hasPart": [
                {
                    "@id": "https://osf.example/482n5",
                    "resourceType": [
                        {"@id": "RegistrationComponent"}
                    ],
                    "dateCreated": [
                        {"@value": "2021-10-18"}
                    ],
                    "creator": [
                        {
                            "@id": "https://osf.example/bhcjn",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Person"}
                            ],
                            "identifier": [
                                {"@value": "https://osf.example/bhcjn"}
                            ],
                            "name": [
                                {"@value": "JW"}
                            ],
                            "affiliation": [
                                {
                                    "@id": "https://ror.example/05d5mza29",
                                    "resourceType": [
                                        {"@id": "Agent"},
                                        {"@id": "Organization"}
                                    ],
                                    "identifier": [
                                        {"@value": "https://ror.example/05d5mza29"}
                                    ],
                                    "name": [
                                        {"@value": "Center For Open Science"}
                                    ]
                                }
                            ]
                        }
                    ],
                    "dateCopyrighted": [
                        {"@value": "2021"}
                    ],
                    "identifier": [
                        {"@value": "https://doi.example/10.17605/OSF.IO/482N5"},
                        {"@value": "https://osf.example/482n5"}
                    ],
                    "publisher": [
                        {
                            "@id": "https://osf.example/registries/osf",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://osf.example/"},
                                {"@value": "https://osf.io/registries/osf"}
                            ],
                            "name": [
                                {"@value": "OSF Registries"}
                            ]
                        }
                    ],
                    "rights": [
                        {
                            "@id": "https://creativecommons.example/licenses/by/4.0/legalcode",
                            "identifier": [
                                {"@value": "https://creativecommons.example/licenses/by/4.0/legalcode"}
                            ],
                            "name": [
                                {"@value": "CC-By Attribution 4.0 International"}
                            ]
                        }
                    ],
                    "title": [
                        {"@value": "IA/IMLS Demo: Child Component"}
                    ],
                    "sameAs": [
                        {"@id": "https://doi.example/10.17605/OSF.IO/482N5"}
                    ],
                    "affiliation": [
                        {
                            "@id": "https://ror.example/05d5mza29",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://ror.example/05d5mza29"}
                            ],
                            "name": [
                                {"@value": "Center For Open Science"}
                            ]
                        }
                    ]
                }
            ],
            "identifier": [
                {"@value": "https://doi.example/10.17605/OSF.IO/2C4ST"},
                {"@value": "https://osf.example/2c4st"}
            ],
            "isVersionOf": [
                {
                    "@id": "https://osf.example/hnm67",
                    "resourceType": [
                        {"@id": "Project"}
                    ],
                    "dateCreated": [
                        {"@value": "2021-10-18"}
                    ],
                    "creator": [
                        {
                            "@id": "https://osf.example/bhcjn",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Person"}
                            ],
                            "identifier": [
                                {"@value": "https://osf.example/bhcjn"}
                            ],
                            "name": [
                                {"@value": "JW"}
                            ],
                            "affiliation": [
                                {
                                    "@id": "https://ror.example/05d5mza29",
                                    "resourceType": [
                                        {"@id": "Agent"},
                                        {"@id": "Organization"}
                                    ],
                                    "identifier": [
                                        {"@value": "https://ror.example/05d5mza29"}
                                    ],
                                    "name": [
                                        {"@value": "Center For Open Science"}
                                    ]
                                }
                            ]
                        }
                    ],
                    "identifier": [
                        {"@value": "https://osf.example/hnm67"}
                    ],
                    "publisher": [
                        {
                            "@id": "https://osf.example",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://osf.example"}
                            ],
                            "name": [
                                {"@value": "OSF"}
                            ]
                        }
                    ],
                    "title": [
                        {"@value": "IA/IMLS Demo"}
                    ],
                    "affiliation": [
                        {
                            "@id": "https://ror.example/05d5mza29",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://ror.example/05d5mza29"}
                            ],
                            "name": [
                                {"@value": "Center For Open Science"}
                            ]
                        }
                    ]
                }
            ],
            "dateModified": [
                {"@value": "2021-10-18"}
            ],
            "publisher": [
                {
                    "@id": "https://osf.example/registries/osf",
                    "resourceType": [
                        {"@id": "Agent"},
                        {"@id": "Organization"}
                    ],
                    "identifier": [
                        {"@value": "https://osf.example/"},
                        {"@value": "https://osf.io/registries/osf"}
                    ],
                    "name": [
                        {"@value": "OSF Registries"}
                    ]
                }
            ],
            "rights": [
                {
                    "@id": "https://creativecommons.example/licenses/by-nc-nd/4.0/legalcode",
                    "identifier": [
                        {"@value": "https://creativecommons.example/licenses/by-nc-nd/4.0/legalcode"}
                    ],
                    "name": [
                        {"@value": "CC-By Attribution-NonCommercial-NoDerivatives 4.0 International"}
                    ]
                }
            ],
            "subject": [
                {
                    "@id": "https://api.osf.example/v2/subjects/584240da54be81056cecaae5",
                    "resourceType": [
                        {"@id": "Concept"}
                    ],
                    "inScheme": [
                        {
                            "@id": "https://bepress.com/reference_guide_dc/disciplines/",
                            "resourceType": [
                                {"@id": "Concept:Scheme"}
                            ],
                            "title": [
                                {"@value": "bepress Digital Commons Three-Tiered Taxonomy"}
                            ]
                        }
                    ],
                    "prefLabel": [
                        {"@value": "Education"}
                    ]
                }
            ],
            "title": [
                {"@value": "IA/IMLS Demo"}
            ],
            "sameAs": [
                {"@id": "https://doi.example/10.17605/OSF.IO/2C4ST"}
            ],
            "affiliation": [
                {
                    "@id": "https://ror.example/05d5mza29",
                    "resourceType": [
                        {"@id": "Agent"},
                        {"@id": "Organization"}
                    ],
                    "identifier": [
                        {"@value": "https://ror.example/05d5mza29"}
                    ],
                    "name": [
                        {"@value": "Center For Open Science"}
                    ]
                }
            ],
            "archivedAt": [
                {"@id": "https://archive.example/details/osf-registrations-2c4st-v1"}
            ],
            "osf:contains": [
                {
                    "@id": "https://osf.example/2ph9b",
                    "resourceType": [
                        {"@id": "File"}
                    ],
                    "dateCreated": [
                        {"@value": "2021-10-18"}
                    ],
                    "identifier": [
                        {"@value": "https://osf.example/2ph9b"}
                    ],
                    "dateModified": [
                        {"@value": "2021-10-18"}
                    ],
                    "fileName": [
                        {"@value": "test_file.txt"}
                    ],
                    "filePath": [
                        {"@value": "/Archive of OSF Storage/test_file.txt"}
                    ],
                    "isContainedBy": [
                        {"@id": "https://osf.example/2c4st"}
                    ]
                }
            ],
            "hostingInstitution": [
                {
                    "@id": "https://cos.example/",
                    "resourceType": [
                        {"@id": "Agent"},
                        {"@id": "Organization"}
                    ],
                    "identifier": [
                        {"@value": "https://cos.example/"},
                        {"@value": "https://ror.example/05d5mza29"}
                    ],
                    "sameAs": [
                        {
                            "@id": "https://ror.example/05d5mza29",
                            "resourceType": [
                                {"@id": "Agent"},
                                {"@id": "Organization"}
                            ],
                            "identifier": [
                                {"@value": "https://ror.example/05d5mza29"}
                            ],
                            "name": [
                                {"@value": "Center For Open Science"}
                            ]
                        }
                    ],
                    "name": [
                        {"@value": "Center for Open Science"}
                    ]
                }
            ],
            "keyword": [
                {"@value": "Demo"},
                {"@value": "IA"},
                {"@value": "IMLS"},
                {"@value": "OSF"}
            ]
        },
    }

    def assert_outputs_equal(self, expected, actual):
        self.assertEqual(expected, json.loads(actual))
