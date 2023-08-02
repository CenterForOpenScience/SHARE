from gather import primitive_rdf, gathering

from share.util.rdfutil import IriLabeler
from trove.vocab.trove import JSONAPI_MEMBERNAME
from trove.vocab.namespaces import OSFMAP, DCTERMS, FOAF, OWL, RDF, RDFS, SKOS, DCMITYPE


# TODO: define as turtle, load in trove.vocab.__init__?
OSFMAP_VOCAB: primitive_rdf.RdfTripleDictionary = {
    ###
    # properties:
    DCTERMS.identifier: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('identifier', language_tag='en'),
        },
    },
    DCTERMS.creator: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('creator', language_tag='en'),
        },
    },
    DCTERMS.title: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('title', language_tag='en'),
        },
    },
    DCTERMS.publisher: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('publisher', language_tag='en'),
        },
    },
    DCTERMS.subject: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('subject', language_tag='en'),
        },
    },
    DCTERMS.contributor: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('contributor', language_tag='en'),
        },
    },
    DCTERMS.language: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('language', language_tag='en'),
        },
    },
    RDF.type: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('resourceType', language_tag='en'),
        },
    },
    DCTERMS.type: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('resourceNature', language_tag='en'),
        },
    },
    DCTERMS.rights: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('rights', language_tag='en'),
        },
    },
    DCTERMS.description: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('description', language_tag='en'),
        },
    },
    OSFMAP.affiliation: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('affiliation', language_tag='en'),
        },
    },
    OSFMAP.affiliatedInstitution: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('affiliatedInstitution', language_tag='en'),
        },
    },
    OSFMAP.hasFunding: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasFunding', language_tag='en'),
        },
    },
    OSFMAP.funder: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('funder', language_tag='en'),
        },
    },
    OSFMAP.keyword: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('keyword', language_tag='en'),
        },
    },
    OWL.sameAs: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('sameAs', language_tag='en'),
        },
    },
    DCTERMS.date: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('date', language_tag='en'),
        },
    },
    DCTERMS.available: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateAvailable', language_tag='en'),
        },
    },
    DCTERMS.dateCopyrighted: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateCopyrighted', language_tag='en'),
        },
    },
    DCTERMS.created: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateCreated', language_tag='en'),
        },
    },
    DCTERMS.modified: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateModified', language_tag='en'),
        },
    },
    DCTERMS.dateSubmitted: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateSubmitted', language_tag='en'),
        },
    },
    DCTERMS.dateAccepted: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateAccepted', language_tag='en'),
        },
    },
    OSFMAP.withdrawn: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateWithdrawn', language_tag='en'),
        },
    },
    OSFMAP.isContainedBy: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('isContainedBy', language_tag='en'),
        },
    },
    DCTERMS.hasPart: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasPart', language_tag='en'),
        },
    },
    DCTERMS.isPartOf: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('isPartOf', language_tag='en'),
        },
    },
    OSFMAP.hasRoot: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasRoot', language_tag='en'),
        },
    },
    DCTERMS.references: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('references', language_tag='en'),
        },
    },
    DCTERMS.hasVersion: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasVersion', language_tag='en'),
        },
    },
    DCTERMS.isVersionOf: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('isVersionOf', language_tag='en'),
        },
    },
    OSFMAP.supplements: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('supplements', language_tag='en'),
        },
    },
    OSFMAP.isSupplementedBy: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('isSupplementedBy', language_tag='en'),
        },
    },
    OSFMAP.archivedAt: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('archivedAt', language_tag='en'),
        },
    },
    OSFMAP.hasAnalyticCodeResource: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasAnalyticCodeResource', language_tag='en'),
        },
    },
    OSFMAP.hasDataResource: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasDataResource', language_tag='en'),
        },
    },
    OSFMAP.hasMaterialsResource: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasMaterialsResource', language_tag='en'),
        },
    },
    OSFMAP.hasPapersResource: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasPapersResource', language_tag='en'),
        },
    },
    OSFMAP.hasSupplementalResource: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasSupplementalResource', language_tag='en'),
        },
    },
    OSFMAP.hasPreregisteredAnalysisPlan: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasPreregisteredAnalysisPlan', language_tag='en'),
        },
    },
    OSFMAP.hasPreregisteredStudyDesign: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasPreregisteredStudyDesign', language_tag='en'),
        },
    },
    OSFMAP.omits: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('omits', language_tag='en'),
        },
    },
    FOAF.name: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('name', language_tag='en'),
        },
    },
    OSFMAP.funderIdentifierType: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('funderIdentifierType', language_tag='en'),
        },
    },
    OSFMAP.awardNumber: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('awardNumber', language_tag='en'),
        },
    },
    OSFMAP.fileName: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('fileName', language_tag='en'),
        },
    },
    OSFMAP.filePath: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('filePath', language_tag='en'),
        },
    },
    OSFMAP.format: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('mediaType', language_tag='en'),
        },
    },
    OSFMAP.versionNumber: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('versionNumber', language_tag='en'),
        },
    },
    OSFMAP.omittedMetadataProperty: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('omittedMetadataProperty', language_tag='en'),
        },
    },
    DCTERMS.conformsTo: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('conformsTo', language_tag='en'),
        },
    },
    OSFMAP.statedConflictOfInterest: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('statedConflictOfInterest', language_tag='en'),
        },
    },
    OSFMAP.isPartOfCollection: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('isPartOfCollection', language_tag='en'),
        },
    },
    SKOS.prefLabel: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('prefLabel', language_tag='en'),
        },
    },
    SKOS.altLabel: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('altLabel', language_tag='en'),
        },
    },
    SKOS.inScheme: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('inScheme', language_tag='en'),
        },
    },
    SKOS.broader: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('broader', language_tag='en'),
        },
    },
    RDFS.label: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('label', language_tag='en'),
        },
    },
    JSONAPI_MEMBERNAME: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('shortFormLabel', language_tag='en'),
        },
    },

    ###
    # types:
    OSFMAP.Project: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('Project', language_tag='en'),
        },
    },
    OSFMAP.ProjectComponent: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('ProjectComponent', language_tag='en'),
        },
    },
    OSFMAP.Registration: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('Registration', language_tag='en'),
        },
    },
    OSFMAP.RegistrationComponent: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('RegistrationComponent', language_tag='en'),
        },
    },
    OSFMAP.Preprint: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('Preprint', language_tag='en'),
        },
    },
    OSFMAP.File: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('File', language_tag='en'),
        },
    },
    DCTERMS.Agent: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('Agent', language_tag='en'),
        },
    },
    OSFMAP.FundingAward: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('FundingAward', language_tag='en'),
        },
    },
    OSFMAP.FileVersion: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('FileVersion', language_tag='en'),
        },
    },
    OSFMAP.OmittedMetadata: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('OmittedMetadata', language_tag='en'),
        },
    },
    FOAF.Person: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('Person', language_tag='en'),
        },
    },
    FOAF.Organization: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('Organization', language_tag='en'),
        },
    },
    RDF.Property: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('Property', language_tag='en'),
        },
    },
    DCMITYPE.Collection: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('Collection', language_tag='en'),
        },
    },
    SKOS.Concept: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('Concept', language_tag='en'),
        },
    },

    ###
    # values:
    OSFMAP['no-conflict-of-interest']: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('no-conflict-of-interest', language_tag='en'),
        },
    },
}


OSFMAP_NORMS = gathering.GatheringNorms(
    namestory=(
        primitive_rdf.text('OSFMAP', language_tag='en'),
        primitive_rdf.text('OSF Metadata Application Profile', language_tag='en'),
        primitive_rdf.text('Open Science Framework Metadata Application Profile', language_tag='en'),
    ),
    vocabulary=OSFMAP_VOCAB,
    focustype_iris={
        OSFMAP.Project,
        OSFMAP.ProjectComponent,
        OSFMAP.Registration,
        OSFMAP.RegistrationComponent,
        OSFMAP.Preprint,
        OSFMAP.File,
        DCTERMS.Agent,
    },
)

osfmap_labeler = IriLabeler(OSFMAP_VOCAB, label_iri=JSONAPI_MEMBERNAME)


ALL_SUGGESTED_PROPERTY_IRIS = [
    DCTERMS.created,
    OSFMAP.funder,
    DCTERMS.subject,
    DCTERMS.rights,
    DCTERMS.type,  # TODO: should this be RDF.type, or does it depend?
    OSFMAP.affiliation,
    DCTERMS.publisher,
    OSFMAP.isPartOfCollection,
    DCTERMS.conformsTo,
    DCTERMS.hasVersion,
    OSFMAP.hasAnalyticCodeResource,
    OSFMAP.hasDataResource,
    OSFMAP.hasMaterialsResource,
    OSFMAP.hasPapersResource,
    OSFMAP.hasPreregisteredAnalysisPlan,
    OSFMAP.hasPreregisteredStudyDesign,
    OSFMAP.hasSupplementalResource,
    OSFMAP.supplements,
]


PROJECT_SUGGESTED_PROPERTY_IRIS = [
    DCTERMS.created,
    OSFMAP.funder,
    DCTERMS.rights,
    DCTERMS.type,
    OSFMAP.affiliation,
    OSFMAP.isPartOfCollection,
    DCTERMS.hasVersion,
    OSFMAP.supplements,
]


REGISTRATION_SUGGESTED_PROPERTY_IRIS = [
    DCTERMS.created,
    OSFMAP.funder,
    DCTERMS.publisher,
    DCTERMS.subject,
    DCTERMS.rights,
    DCTERMS.type,
    OSFMAP.affiliation,
    DCTERMS.conformsTo,
    DCTERMS.hasVersion,
    OSFMAP.hasAnalyticCodeResource,
    OSFMAP.hasDataResource,
    OSFMAP.hasMaterialsResource,
    OSFMAP.hasPapersResource,
    OSFMAP.hasSupplementalResource,
    OSFMAP.supplements,
]


PREPRINT_SUGGESTED_PROPERTY_IRIS = [
    DCTERMS.created,
    DCTERMS.subject,
    DCTERMS.rights,
    DCTERMS.publisher,
    DCTERMS.hasVersion,
    OSFMAP.hasDataResource,
    OSFMAP.hasPreregisteredAnalysisPlan,
    OSFMAP.hasPreregisteredStudyDesign,
    OSFMAP.supplements,
]


AGENT_SUGGESTED_PROPERTY_IRIS = [
    OSFMAP.affiliation,
]


def suggested_property_iris(type_iris: set[str]) -> list[str]:
    if not type_iris or not type_iris.issubset(OSFMAP_NORMS.focustype_iris):
        return []
    if type_iris == {DCTERMS.Agent}:
        return AGENT_SUGGESTED_PROPERTY_IRIS
    if type_iris == {OSFMAP.Preprint}:
        return PREPRINT_SUGGESTED_PROPERTY_IRIS
    if type_iris <= {OSFMAP.Project, OSFMAP.ProjectComponent}:
        return PROJECT_SUGGESTED_PROPERTY_IRIS
    if type_iris <= {OSFMAP.Registration, OSFMAP.RegistrationComponent}:
        return REGISTRATION_SUGGESTED_PROPERTY_IRIS
    return ALL_SUGGESTED_PROPERTY_IRIS


def is_date_property(property_iri):
    # TODO: better inference (rdfs:range?)
    return property_iri in {
        DCTERMS.date,
        DCTERMS.available,
        DCTERMS.created,
        DCTERMS.modified,
        DCTERMS.dateCopyrighted,
        DCTERMS.dateSubmitted,
        DCTERMS.dateAccepted,
        OSFMAP.withdrawn,
    }
