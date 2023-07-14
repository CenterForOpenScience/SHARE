from gather import (
    text,
    OWL,
    RDF,
    RDFS,
    RdfTripleDictionary,
    GatheringNorms,
)

from share.util.rdfutil import IriLabeler
from trove.vocab.trove import JSONAPI_MEMBERNAME
from trove.vocab.iri_namespace import OSFMAP, DCTERMS, FOAF


# TODO: define as turtle, load in trove.vocab.__init__?
OSFMAP_VOCAB: RdfTripleDictionary = {
    ###
    # properties:
    DCTERMS.identifier: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('identifier', language_tag='en'),
        },
    },
    DCTERMS.creator: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('creator', language_tag='en'),
        },
    },
    DCTERMS.title: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('title', language_tag='en'),
        },
    },
    DCTERMS.publisher: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('publisher', language_tag='en'),
        },
    },
    DCTERMS.subject: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('subject', language_tag='en'),
        },
    },
    DCTERMS.contributor: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('contributor', language_tag='en'),
        },
    },
    DCTERMS.language: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('language', language_tag='en'),
        },
    },
    RDF.type: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('resourceType', language_tag='en'),
        },
    },
    DCTERMS.type: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('resourceNature', language_tag='en'),
        },
    },
    DCTERMS.rights: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('rights', language_tag='en'),
        },
    },
    DCTERMS.description: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('description', language_tag='en'),
        },
    },
    OSFMAP.affiliation: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('affiliation', language_tag='en'),
        },
    },
    OSFMAP.affiliatedInstitution: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('affiliatedInstitution', language_tag='en'),
        },
    },
    OSFMAP.funder: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('funder', language_tag='en'),
        },
    },
    OSFMAP.keyword: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('keyword', language_tag='en'),
        },
    },
    OWL.sameAs: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('sameAs', language_tag='en'),
        },
    },
    DCTERMS.date: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('date', language_tag='en'),
        },
    },
    DCTERMS.available: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('dateAvailable', language_tag='en'),
        },
    },
    DCTERMS.dateCopyrighted: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('dateCopyrighted', language_tag='en'),
        },
    },
    DCTERMS.created: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('dateCreated', language_tag='en'),
        },
    },
    DCTERMS.modified: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('dateModified', language_tag='en'),
        },
    },
    DCTERMS.dateSubmitted: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('dateSubmitted', language_tag='en'),
        },
    },
    DCTERMS.dateAccepted: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('dateAccepted', language_tag='en'),
        },
    },
    OSFMAP.withdrawn: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('dateWithdrawn', language_tag='en'),
        },
    },
    OSFMAP.isContainedBy: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('isContainedBy', language_tag='en'),
        },
    },
    DCTERMS.hasPart: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('hasPart', language_tag='en'),
        },
    },
    DCTERMS.isPartOf: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('isPartOf', language_tag='en'),
        },
    },
    OSFMAP.hasRoot: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('hasRoot', language_tag='en'),
        },
    },
    DCTERMS.references: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('references', language_tag='en'),
        },
    },
    DCTERMS.hasVersion: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('hasVersion', language_tag='en'),
        },
    },
    DCTERMS.isVersionOf: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('isVersionOf', language_tag='en'),
        },
    },
    OSFMAP.supplements: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('supplements', language_tag='en'),
        },
    },
    OSFMAP.isSupplementedBy: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('isSupplementedBy', language_tag='en'),
        },
    },
    OSFMAP.archivedAt: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('archivedAt', language_tag='en'),
        },
    },
    OSFMAP.hasAnalyticCodeResource: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('hasAnalyticCodeResource', language_tag='en'),
        },
    },
    OSFMAP.hasDataResource: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('hasDataResource', language_tag='en'),
        },
    },
    OSFMAP.hasMaterialsResource: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('hasMaterialsResource', language_tag='en'),
        },
    },
    OSFMAP.hasPapersResource: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('hasPapersResource', language_tag='en'),
        },
    },
    OSFMAP.hasSupplementalResource: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('hasSupplementalResource', language_tag='en'),
        },
    },
    OSFMAP.hasPreregisteredAnalysisPlan: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('hasPreregisteredAnalysisPlan', language_tag='en'),
        },
    },
    OSFMAP.hasPreregisteredStudyDesign: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('hasPreregisteredStudyDesign', language_tag='en'),
        },
    },
    OSFMAP.omits: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('omits', language_tag='en'),
        },
    },
    FOAF.name: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('name', language_tag='en'),
        },
    },
    OSFMAP.funderIdentifierType: {
        RDF.type: {RDF.Property, OSFMAP.RelationshipProperty},
        JSONAPI_MEMBERNAME: {
            text('funderIdentifierType', language_tag='en'),
        },
    },
    OSFMAP.awardNumber: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('awardNumber', language_tag='en'),
        },
    },
    OSFMAP.awardURI: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('awardURI', language_tag='en'),
        },
    },
    OSFMAP.awardTitle: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('awardTitle', language_tag='en'),
        },
    },
    OSFMAP.fileName: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('fileName', language_tag='en'),
        },
    },
    OSFMAP.filePath: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('filePath', language_tag='en'),
        },
    },
    OSFMAP.format: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('mediaType', language_tag='en'),
        },
    },
    OSFMAP.versionNumber: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('versionNumber', language_tag='en'),
        },
    },
    OSFMAP.omittedMetadataProperty: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('omittedMetadataProperty', language_tag='en'),
        },
    },
    OSFMAP.statedConflictOfInterest: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('statedConflictOfInterest', language_tag='en'),
        },
    },

    ###
    # types:
    OSFMAP.Project: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('Project', language_tag='en'),
        },
    },
    OSFMAP.ProjectComponent: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('ProjectComponent', language_tag='en'),
        },
    },
    OSFMAP.Registration: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('Registration', language_tag='en'),
        },
    },
    OSFMAP.RegistrationComponent: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('RegistrationComponent', language_tag='en'),
        },
    },
    OSFMAP.Preprint: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('Preprint', language_tag='en'),
        },
    },
    OSFMAP.File: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('File', language_tag='en'),
        },
    },
    OSFMAP.Agent: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('Agent', language_tag='en'),
        },
    },
    OSFMAP.Funder: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('Funder', language_tag='en'),
        },
    },
    OSFMAP.FileVersion: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('FileVersion', language_tag='en'),
        },
    },
    OSFMAP.OmittedMetadata: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('OmittedMetadata', language_tag='en'),
        },
    },
    FOAF.Person: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('Person', language_tag='en'),
        },
    },
    FOAF.Organization: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            text('Organization', language_tag='en'),
        },
    },

    ###
    # values:
    OSFMAP['no-conflict-of-interest']: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            text('no-conflict-of-interest', language_tag='en'),
        },
    },
}


OSFMAP_NORMS = GatheringNorms(
    namestory=(
        text('OSFMAP', language_tag='en'),
        text('OSF Metadata Application Profile', language_tag='en'),
        text('Open Science Framework Metadata Application Profile', language_tag='en'),
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

osfmap_labeler = IriLabeler(OSFMAP_VOCAB, label_iri=JSONAPI_MEMBERNAME)
