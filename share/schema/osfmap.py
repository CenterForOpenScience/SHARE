from gather import (
    text,
    IriNamespace,
    OWL,
    RDF,
    RDFS,
    IANA_LANGUAGE,
    RdfTripleDictionary,
    GatheringNorms,
)

from share.util.rdfutil import IriLabeler


# standard namespaces:
DCTERMS = IriNamespace('http://purl.org/dc/terms/')
FOAF = IriNamespace('http://xmlns.com/foaf/0.1/')
RFC3339 = IriNamespace('https://www.rfc-editor.org/rfc/rfc3339.txt#')
FULL_DATE = RFC3339['full-date']

# defined but evolving:
OSFMAP = IriNamespace('https://osf.io/vocab/2023/')
OSFMAP_VOCAB: RdfTripleDictionary = {

    ###
    # properties:
    DCTERMS.identifier: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('identifier', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.creator: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('creator', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.title: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('title', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.publisher: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('publisher', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.subject: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('subject', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.contributor: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('contributor', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.language: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('language', language_iris={IANA_LANGUAGE.en}),
        },
    },
    RDF.type: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('resourceType', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.type: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('resourceNature', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.rights: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('rights', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.description: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('description', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.affiliation: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('affiliation', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.affiliatedInstitution: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('affiliatedInstitution', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.funder: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('funder', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.keyword: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('keyword', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OWL.sameAs: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('sameAs', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.date: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('date', language_iris={FULL_DATE}),
        },
    },
    DCTERMS.available: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('dateAvailable', language_iris={FULL_DATE}),
        },
    },
    DCTERMS.dateCopyrighted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('dateCopyrighted', language_iris={FULL_DATE}),
        },
    },
    DCTERMS.created: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('dateCreated', language_iris={FULL_DATE}),
        },
    },
    DCTERMS.modified: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('dateModified', language_iris={FULL_DATE}),
        },
    },
    DCTERMS.dateSubmitted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('dateSubmitted', language_iris={FULL_DATE}),
        },
    },
    DCTERMS.dateAccepted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('dateAccepted', language_iris={FULL_DATE}),
        },
    },
    OSFMAP.withdrawn: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('dateWithdrawn', language_iris={FULL_DATE}),
        },
    },
    OSFMAP.isContainedBy: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('isContainedBy', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.hasPart: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('hasPart', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.isPartOf: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('isPartOf', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.hasRoot: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('hasRoot', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.references: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('references', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.hasVersion: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('hasVersion', language_iris={IANA_LANGUAGE.en}),
        },
    },
    DCTERMS.isVersionOf: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('isVersionOf', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.supplements: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('supplements', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.isSupplementedBy: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('isSupplementedBy', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.archivedAt: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('archivedAt', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.hasAnalyticCodeResource: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('hasAnalyticCodeResource', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.hasDataResource: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('hasDataResource', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.hasMaterialsResource: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('hasMaterialsResource', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.hasPapersResource: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('hasPapersResource', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.hasSupplementalResource: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('hasSupplementalResource', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.hasPreregisteredAnalysisPlan: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('hasPreregisteredAnalysisPlan', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.hasPreregisteredStudyPlan: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('hasPreregisteredStudyPlan', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.omits: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('omits', language_iris={IANA_LANGUAGE.en}),
        },
    },
    FOAF.name: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('name', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.funderIdentifierType: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        RDFS.label: {
            text('funderIdentifierType', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.awardNumber: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('awardNumber', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.awardURI: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('awardURI', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.awardTitle: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('awardTitle', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.fileName: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('fileName', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.filePath: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('filePath', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.format: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('mediaType', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.versionNumber: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('versionNumber', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.omittedMetadataProperty: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            text('omittedMetadataProperty', language_iris={IANA_LANGUAGE.en}),
        },
    },

    ###
    # types:
    OSFMAP.Project: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('Project', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.ProjectComponent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('ProjectComponent', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.Registration: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('Registration', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.RegistrationComponent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('RegistrationComponent', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.Preprint: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('Preprint', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.File: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('File', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.Agent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('Agent', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.Funder: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('Funder', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.FileVersion: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('FileVersion', language_iris={IANA_LANGUAGE.en}),
        },
    },
    OSFMAP.OmittedMetadata: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('OmittedMetadata', language_iris={IANA_LANGUAGE.en}),
        },
    },
    FOAF.Person: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('Person', language_iris={IANA_LANGUAGE.en}),
        },
    },
    FOAF.Organization: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            text('Organization', language_iris={IANA_LANGUAGE.en}),
        },
    },
}


OSFMAP_NORMS = GatheringNorms(
    namestory=(
        text('OSFMAP', language_iris={IANA_LANGUAGE.en}),
        text('OSF Metadata Application Profile', language_iris={IANA_LANGUAGE.en}),
        text('Open Science Framework Metadata Application Profile', language_iris={IANA_LANGUAGE.en}),
    ),
    vocabulary=OSFMAP_VOCAB,
    focustype_iris={
        OSFMAP.Project,
        OSFMAP.ProjectComponent,
        OSFMAP.Registration,
        OSFMAP.RegistrationComponent,
        OSFMAP.Preprint,
        OSFMAP.File,
        # TODO?: OSFMAP.Agent,
    },
)

osfmap_labeler = IriLabeler(OSFMAP_VOCAB)
