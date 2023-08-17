from gather import primitive_rdf, gathering

from trove.util.iri_labeler import IriLabeler
from trove.vocab.trove import JSONAPI_MEMBERNAME
from trove.vocab.namespaces import OSFMAP, DCTERMS, FOAF, OWL, RDF, RDFS, SKOS, DCMITYPE


# TODO: define as turtle, load in trove.vocab.__init__?
OSFMAP_VOCAB: primitive_rdf.RdfTripleDictionary = {
    ###
    # properties:
    DCTERMS.identifier: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Identifier', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('identifier', language_tag='en'),
        },
    },
    DCTERMS.creator: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Creator', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('creator', language_tag='en'),
        },
    },
    DCTERMS.title: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Title', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('title', language_tag='en'),
        },
    },
    DCTERMS.publisher: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Provider', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('publisher', language_tag='en'),
        },
    },
    DCTERMS.subject: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Subject', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('subject', language_tag='en'),
        },
    },
    DCTERMS.contributor: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Contributor', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('contributor', language_tag='en'),
        },
    },
    DCTERMS.language: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Language', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('language', language_tag='en'),
        },
    },
    RDF.type: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Resource type', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('resourceType', language_tag='en'),
        },
    },
    DCTERMS.type: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Resource type (general)', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('resourceNature', language_tag='en'),
        },
    },
    DCTERMS.rights: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('License', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('rights', language_tag='en'),
        },
    },
    DCTERMS.description: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Description', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('description', language_tag='en'),
        },
    },
    OSFMAP.affiliation: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Institution', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('affiliation', language_tag='en'),
        },
    },
    OSFMAP.hasFunding: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Funding award', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasFunding', language_tag='en'),
        },
    },
    OSFMAP.funder: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Funder', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('funder', language_tag='en'),
        },
    },
    OSFMAP.keyword: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Tag', language_tag='en'),
        },
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
        RDFS.label: {
            primitive_rdf.text('Date', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('date', language_tag='en'),
        },
    },
    DCTERMS.available: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Date available', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateAvailable', language_tag='en'),
        },
    },
    DCTERMS.dateCopyrighted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Date copyrighted', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateCopyrighted', language_tag='en'),
        },
    },
    DCTERMS.created: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Date created', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateCreated', language_tag='en'),
        },
    },
    DCTERMS.modified: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Date modified', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateModified', language_tag='en'),
        },
    },
    DCTERMS.dateSubmitted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Date submitted', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateSubmitted', language_tag='en'),
        },
    },
    DCTERMS.dateAccepted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Date accepted', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateAccepted', language_tag='en'),
        },
    },
    OSFMAP.dateWithdrawn: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Date withdrawn', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('dateWithdrawn', language_tag='en'),
        },
    },
    OSFMAP.isContainedBy: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Is contained by', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('isContainedBy', language_tag='en'),
        },
    },
    DCTERMS.hasPart: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Has component', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasPart', language_tag='en'),
        },
    },
    DCTERMS.isPartOf: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Is component of', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('isPartOf', language_tag='en'),
        },
    },
    OSFMAP.hasRoot: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Has root', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasRoot', language_tag='en'),
        },
    },
    DCTERMS.references: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('References', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('references', language_tag='en'),
        },
    },
    DCTERMS.hasVersion: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Has version', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasVersion', language_tag='en'),
        },
    },
    DCTERMS.isVersionOf: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Is version of', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('isVersionOf', language_tag='en'),
        },
    },
    OSFMAP.supplements: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Supplements', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('supplements', language_tag='en'),
        },
    },
    OSFMAP.isSupplementedBy: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Is supplemented by', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('isSupplementedBy', language_tag='en'),
        },
    },
    OSFMAP.archivedAt: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Archived at', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('archivedAt', language_tag='en'),
        },
    },
    OSFMAP.hasAnalyticCodeResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Analytic code', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasAnalyticCodeResource', language_tag='en'),
        },
    },
    OSFMAP.hasDataResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Data', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasDataResource', language_tag='en'),
        },
    },
    OSFMAP.hasMaterialsResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Materials', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasMaterialsResource', language_tag='en'),
        },
    },
    OSFMAP.hasPapersResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Papers resource', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasPapersResource', language_tag='en'),
        },
    },
    OSFMAP.hasSupplementalResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Supplemental resource', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasSupplementalResource', language_tag='en'),
        },
    },
    OSFMAP.hasPreregisteredAnalysisPlan: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Preregistered analysis plan', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasPreregisteredAnalysisPlan', language_tag='en'),
        },
    },
    OSFMAP.hasPreregisteredStudyDesign: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Preregistered study design', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('hasPreregisteredStudyDesign', language_tag='en'),
        },
    },
    OSFMAP.omits: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Omits metadata', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('omits', language_tag='en'),
        },
    },
    FOAF.name: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Name', language_tag='en'),
        },
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
        RDFS.label: {
            primitive_rdf.text('Award number', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('awardNumber', language_tag='en'),
        },
    },
    OSFMAP.fileName: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('File name', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('fileName', language_tag='en'),
        },
    },
    OSFMAP.filePath: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('File path', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('filePath', language_tag='en'),
        },
    },
    OSFMAP.format: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Media type', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('mediaType', language_tag='en'),
        },
    },
    OSFMAP.versionNumber: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Version number', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('versionNumber', language_tag='en'),
        },
    },
    OSFMAP.omittedMetadataProperty: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Omitted property', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('omittedMetadataProperty', language_tag='en'),
        },
    },
    DCTERMS.conformsTo: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Registration template', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('conformsTo', language_tag='en'),
        },
    },
    OSFMAP.statedConflictOfInterest: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Stated conflict of interest', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('statedConflictOfInterest', language_tag='en'),
        },
    },
    OSFMAP.isPartOfCollection: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('Is part of collection', language_tag='en'),
        },
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
        RDFS.label: {
            primitive_rdf.text('Label', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('displayLabel', language_tag='en'),
        },
    },
    JSONAPI_MEMBERNAME: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.text('JSON:API member name', language_tag='en'),
        },
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
        RDFS.label: {
            primitive_rdf.text('Creator asserts no conflict of interest.', language_tag='en'),
        },
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

osfmap_labeler = IriLabeler(
    OSFMAP_VOCAB,
    label_iri=JSONAPI_MEMBERNAME,
    acceptable_prefixes=('osf:', 'osfmap:'),
)


ALL_SUGGESTED_PROPERTY_PATHS = (
    (DCTERMS.created,),
    (OSFMAP.funder,),
    (DCTERMS.subject,),
    (DCTERMS.rights,),
    (DCTERMS.type,),
    (OSFMAP.affiliation,),
    (DCTERMS.publisher,),
    (OSFMAP.isPartOfCollection,),
    (DCTERMS.conformsTo,),
    (OSFMAP.hasAnalyticCodeResource,),
    (OSFMAP.hasDataResource,),
    (OSFMAP.hasMaterialsResource,),
    (OSFMAP.hasPapersResource,),
    (OSFMAP.hasPreregisteredAnalysisPlan,),
    (OSFMAP.hasPreregisteredStudyDesign,),
    (OSFMAP.hasSupplementalResource,),
    (OSFMAP.supplements,),
)


PROJECT_SUGGESTED_PROPERTY_PATHS = (
    (DCTERMS.created,),
    (OSFMAP.funder,),
    (DCTERMS.rights,),
    (DCTERMS.type,),
    (OSFMAP.affiliation,),
    (OSFMAP.isPartOfCollection,),
    (OSFMAP.supplements,),
)


REGISTRATION_SUGGESTED_PROPERTY_PATHS = (
    (DCTERMS.created,),
    (OSFMAP.funder,),
    (DCTERMS.publisher,),
    (DCTERMS.subject,),
    (DCTERMS.rights,),
    (DCTERMS.type,),
    (OSFMAP.affiliation,),
    (DCTERMS.conformsTo,),
    (OSFMAP.hasAnalyticCodeResource,),
    (OSFMAP.hasDataResource,),
    (OSFMAP.hasMaterialsResource,),
    (OSFMAP.hasPapersResource,),
    (OSFMAP.hasSupplementalResource,),
    (OSFMAP.supplements,),
)


PREPRINT_SUGGESTED_PROPERTY_PATHS = (
    (DCTERMS.created,),
    (DCTERMS.subject,),
    (DCTERMS.rights,),
    (DCTERMS.publisher,),
    (OSFMAP.hasDataResource,),
    (OSFMAP.hasPreregisteredAnalysisPlan,),
    (OSFMAP.hasPreregisteredStudyDesign,),
    (OSFMAP.supplements,),
)


FILE_SUGGESTED_PROPERTY_PATHS = (
    (DCTERMS.created,),
    (DCTERMS.type,),
    (OSFMAP.isContainedBy, OSFMAP.funder,),
    (OSFMAP.isContainedBy, DCTERMS.rights,),
)


AGENT_SUGGESTED_PROPERTY_PATHS = (
    (OSFMAP.affiliation,),
)


def suggested_property_paths(type_iris: set[str]) -> tuple[tuple[str, ...]]:
    if not type_iris or not type_iris.issubset(OSFMAP_NORMS.focustype_iris):
        return ()
    if type_iris == {DCTERMS.Agent}:
        return AGENT_SUGGESTED_PROPERTY_PATHS
    if type_iris == {OSFMAP.Preprint}:
        return PREPRINT_SUGGESTED_PROPERTY_PATHS
    if type_iris == {OSFMAP.File}:
        return FILE_SUGGESTED_PROPERTY_PATHS
    if type_iris <= {OSFMAP.Project, OSFMAP.ProjectComponent}:
        return PROJECT_SUGGESTED_PROPERTY_PATHS
    if type_iris <= {OSFMAP.Registration, OSFMAP.RegistrationComponent}:
        return REGISTRATION_SUGGESTED_PROPERTY_PATHS
    return ALL_SUGGESTED_PROPERTY_PATHS


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
