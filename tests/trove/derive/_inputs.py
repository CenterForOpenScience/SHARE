from datetime import date
import dataclasses
from primitive_metadata import primitive_rdf as rdf

from trove.vocab.namespaces import (
    SKOS,
    DCAT,
    RDF,
    DCTERMS,
    OSFMAP,
    FOAF,
    OWL,
    SHAREv2,
)


BLARG = rdf.IriNamespace('http://blarg.example/vocab/')


@dataclasses.dataclass
class DeriverTestDoc:
    focus_iri: str
    tripledict: rdf.RdfTripleDictionary


DERIVER_TEST_DOCS: dict[str, DeriverTestDoc] = {
    'blarg-item': DeriverTestDoc(BLARG.my_item, {
        BLARG.my_item: {
            RDF.type: {BLARG.Item},
            DCTERMS.title: {rdf.literal('title', language='en')},
            DCTERMS.creator: {BLARG.me},
            DCTERMS.created: {rdf.literal('2024-02-14')},
        },
        BLARG.me: {
            RDF.type: {FOAF.Person},
            FOAF.name: {rdf.literal('me me')},
        },
    }),
    'blarg-project': DeriverTestDoc(BLARG.my_project, {
        BLARG.my_project: {
            RDF.type: {BLARG.Item, OSFMAP.Project},
            DCTERMS.title: {rdf.literal('title', language='en')},
            DCTERMS.creator: {BLARG.ME},
            DCTERMS.created: {rdf.literal('2024-02-14')},
        },
        BLARG.me: {
            RDF.type: {FOAF.Person},
            FOAF.name: {rdf.literal('me me')},
        },
    }),
    'sharev2-with-subjects': DeriverTestDoc('http://osf.example/chair/', {
        'http://osf.example/chair/': {
            RDF.type: {
                SHAREv2.CreativeWork,
                SHAREv2.Publication,
                SHAREv2.Registration,
            },
            DCTERMS.conformsTo: {
                rdf.blanknode({FOAF.name: {rdf.literal("Open-Ended Registration")}}),
            },
            DCTERMS.created: {rdf.literal(date(2019, 1, 23))},
            DCTERMS.creator: {'mailto:rando@example.com'},
            DCTERMS.date: {rdf.literal(date(2019, 1, 23))},
            DCTERMS.identifier: {rdf.literal("http://osf.example/chair/")},
            DCTERMS.isPartOf: {'http://osf.example/vroom/'},
            DCTERMS.subject: {
                rdf.literal('Architecture'),
                rdf.literal('Biology'),
                rdf.literal('Custom biologyyyy'),
                rdf.literal('bepress|Architecture'),
                rdf.literal('bepress|Life Sciences|Biology'),
                rdf.literal('foo|Custom life sciencesssss|Custom biologyyyy'),
            },
            DCTERMS.title: {rdf.literal("Assorted chair")},
            OSFMAP.affiliation: {'http://wassa.example'},
        },
        'http://osf.example/mdept/': {
            RDF.type: {
                SHAREv2.CreativeWork,
                SHAREv2.Publication,
                SHAREv2.Registration,
            },
            DCTERMS.identifier: {rdf.literal('http://osf.example/mdept/')},
            DCTERMS.title: {rdf.literal("Miscellaneous department")},
        },
        'http://osf.example/vroom/': {
            RDF.type: {
                SHAREv2.CreativeWork,
                SHAREv2.Publication,
                SHAREv2.Registration,
            },
            DCTERMS.identifier: {rdf.literal('http://osf.example/vroom/')},
            DCTERMS.isPartOf: {'http://osf.example/mdept/'},
            DCTERMS.title: {rdf.literal("Various room")},
        },
        'mailto:rando@example.com': {
            RDF.type: {
                FOAF.Person,
                SHAREv2.Agent,
                SHAREv2.Person,
            },
            DCTERMS.identifier: {
                rdf.literal('http://osf.example/rando/'),
                rdf.literal('mailto:rando@example.com'),
            },
            OWL.sameAs: {'http://osf.example/rando/'},
            FOAF.name: {rdf.literal('Some Rando')},
            OSFMAP.affiliation: {'http://wassa.example'},
        },
        'http://wassa.example': {
            RDF.type: {
                FOAF.Organization,
                SHAREv2.Agent,
                SHAREv2.Institution,
                SHAREv2.Organization,
            },
            FOAF.name: {rdf.literal('Wassamatter University')},
        },
    }),
    'osfmap-registration': DeriverTestDoc('https://osf.example/2c4st', {
        'https://api.osf.example/v2/schemas/registrations/564d31db8c5e4a7c9694b2be/': {
            DCTERMS.title: {rdf.literal("Open-Ended Registration")},
        },
        'https://api.osf.example/v2/subjects/584240da54be81056cecaae5': {
            RDF.type: {SKOS.Concept},
            SKOS.inScheme: {'https://bepress.com/reference_guide_dc/disciplines/'},
            SKOS.prefLabel: {rdf.literal('Education')},
        },
        'https://bepress.com/reference_guide_dc/disciplines/': {
            RDF.type: {SKOS.ConceptScheme},
            DCTERMS.title: {rdf.literal('bepress Digital Commons Three-Tiered Taxonomy')},
        },
        'https://cos.example/': {
            RDF.type: {DCTERMS.Agent, FOAF.Organization},
            DCTERMS.identifier: {rdf.literal('https://cos.example/'), rdf.literal('https://ror.example/05d5mza29')},
            OWL.sameAs: {'https://ror.example/05d5mza29'},
            FOAF.name: {rdf.literal('Center for Open Science')},
        },
        'https://creativecommons.example/licenses/by-nc-nd/4.0/legalcode': {
            DCTERMS.identifier: {rdf.literal('https://creativecommons.example/licenses/by-nc-nd/4.0/legalcode')},
            FOAF.name: {rdf.literal('CC-By Attribution-NonCommercial-NoDerivatives 4.0 International')},
        },
        'https://creativecommons.example/licenses/by/4.0/legalcode': {
            DCTERMS.identifier: {rdf.literal('https://creativecommons.example/licenses/by/4.0/legalcode')},
            FOAF.name: {rdf.literal('CC-By Attribution 4.0 International')},
        },
        'https://osf.example/2c4st': {
            RDF.type: {OSFMAP.Registration},
            DCTERMS.conformsTo: {'https://api.osf.example/v2/schemas/registrations/564d31db8c5e4a7c9694b2be/'},
            DCTERMS.created: {date(2021, 10, 18)},
            DCTERMS.creator: {'https://osf.example/bhcjn'},
            DCTERMS.dateCopyrighted: {rdf.literal('2021')},
            DCTERMS.description: {rdf.literal('This registration tree is intended to demonstrate linkages between the OSF view of a Registration and the Internet Archive view')},
            DCTERMS.hasPart: {'https://osf.example/482n5'},
            DCTERMS.identifier: {rdf.literal('https://doi.example/10.17605/OSF.IO/2C4ST'), rdf.literal('https://osf.example/2c4st')},
            DCTERMS.isVersionOf: {'https://osf.example/hnm67'},
            DCTERMS.modified: {date(2021, 10, 18)},
            DCTERMS.publisher: {'https://osf.example/registries/osf'},
            DCTERMS.rights: {'https://creativecommons.example/licenses/by-nc-nd/4.0/legalcode'},
            DCTERMS.subject: {'https://api.osf.example/v2/subjects/584240da54be81056cecaae5'},
            DCTERMS.title: {rdf.literal('IA/IMLS Demo')},
            OWL.sameAs: {'https://doi.example/10.17605/OSF.IO/2C4ST'},
            DCAT.accessService: {'https://osf.example'},
            OSFMAP.affiliation: {'https://ror.example/05d5mza29'},
            OSFMAP.archivedAt: {'https://archive.example/details/osf-registrations-2c4st-v1'},
            OSFMAP.contains: {'https://osf.example/2ph9b'},
            OSFMAP.hostingInstitution: {'https://cos.example/'},
            OSFMAP.keyword: {rdf.literal('Demo'), rdf.literal('IA'), rdf.literal('IMLS'), rdf.literal('OSF')},
        },
        'https://osf.example/2ph9b': {
            RDF.type: {OSFMAP.File},
            DCTERMS.created: {date(2021, 10, 18)},
            DCTERMS.identifier: {rdf.literal('https://osf.example/2ph9b')},
            DCTERMS.modified: {date(2021, 10, 18)},
            OSFMAP.fileName: {rdf.literal('test_file.txt')},
            OSFMAP.filePath: {rdf.literal('/Archive of OSF Storage/test_file.txt')},
            OSFMAP.isContainedBy: {'https://osf.example/2c4st'},
        },
        'https://osf.example/482n5': {
            RDF.type: {OSFMAP.RegistrationComponent},
            DCTERMS.created: {date(2021, 10, 18)},
            DCTERMS.creator: {'https://osf.example/bhcjn'},
            DCTERMS.dateCopyrighted: {rdf.literal('2021')},
            DCTERMS.identifier: {rdf.literal('https://doi.example/10.17605/OSF.IO/482N5'), rdf.literal('https://osf.example/482n5')},
            DCTERMS.publisher: {'https://osf.example/registries/osf'},
            DCTERMS.rights: {'https://creativecommons.example/licenses/by/4.0/legalcode'},
            DCTERMS.title: {rdf.literal('IA/IMLS Demo: Child Component')},
            OWL.sameAs: {'https://doi.example/10.17605/OSF.IO/482N5'},
            OSFMAP.affiliation: {'https://ror.example/05d5mza29'},
        },
        'https://osf.example/hnm67': {
            RDF.type: {OSFMAP.Project},
            DCTERMS.created: {date(2021, 10, 18)},
            DCTERMS.creator: {'https://osf.example/bhcjn'},
            DCTERMS.identifier: {rdf.literal('https://osf.example/hnm67')},
            DCTERMS.publisher: {'https://osf.example'},
            DCTERMS.title: {rdf.literal('IA/IMLS Demo')},
            OSFMAP.affiliation: {'https://ror.example/05d5mza29'},
        },
        'https://osf.example': {
            RDF.type: {DCTERMS.Agent, FOAF.Organization},
            DCTERMS.identifier: {rdf.literal('https://osf.example')},
            FOAF.name: {rdf.literal('OSF')},
        },
        'https://osf.example/registries/osf': {
            RDF.type: {DCTERMS.Agent, FOAF.Organization},
            DCTERMS.identifier: {rdf.literal('https://osf.example/'), rdf.literal('https://osf.io/registries/osf')},
            FOAF.name: {rdf.literal('OSF Registries')},
        },
        'https://osf.example/bhcjn': {
            RDF.type: {DCTERMS.Agent, FOAF.Person},
            DCTERMS.identifier: {rdf.literal('https://osf.example/bhcjn')},
            FOAF.name: {rdf.literal('JW')},
            OSFMAP.affiliation: {'https://ror.example/05d5mza29'},
        },
        'https://ror.example/05d5mza29': {
            RDF.type: {DCTERMS.Agent, FOAF.Organization},
            DCTERMS.identifier: {rdf.literal('https://ror.example/05d5mza29')},
            FOAF.name: {rdf.literal('Center For Open Science')},
        },
    }),
}
