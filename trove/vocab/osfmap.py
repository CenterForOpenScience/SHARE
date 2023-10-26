from primitive_metadata import primitive_rdf, gather

from share.models.feature_flag import FeatureFlag
from trove.util.iri_labeler import IriLabeler
from trove.vocab.trove import JSONAPI_MEMBERNAME
from trove.vocab.namespaces import (
    DCAT,
    DCMITYPE,
    DCTERMS,
    FOAF,
    OSFMAP,
    OWL,
    RDF,
    RDFS,
    SKOS,
    TROVE,
)


# TODO: define as turtle, load in trove.vocab.__init__?
OSFMAP_VOCAB: primitive_rdf.RdfTripleDictionary = {
    ###
    # properties:
    DCTERMS.identifier: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Identifier', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('identifier', language_tag='en'),
        },
    },
    DCTERMS.creator: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Creator', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('creator', language_tag='en'),
        },
    },
    DCTERMS.title: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Title', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('title', language_tag='en'),
        },
    },
    DCTERMS.publisher: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Provider', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('publisher', language_tag='en'),
        },
    },
    DCTERMS.subject: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Subject', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('subject', language_tag='en'),
        },
    },
    DCTERMS.contributor: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Contributor', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('contributor', language_tag='en'),
        },
    },
    DCTERMS.language: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Language', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('language', language_tag='en'),
        },
    },
    RDF.type: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('resourceType', language_tag='en'),
        },
    },
    DCTERMS.type: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Resource type', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('resourceNature', language_tag='en'),
        },
    },
    DCTERMS.rights: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('License', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('rights', language_tag='en'),
        },
    },
    DCTERMS.rightsHolder: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('License holder', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('rightsHolder', language_tag='en'),
        },
    },
    DCTERMS.description: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Description', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('description', language_tag='en'),
        },
    },
    OSFMAP.affiliation: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Institution', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('affiliation', language_tag='en'),
        },
    },
    OSFMAP.hasFunding: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Funding award', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasFunding', language_tag='en'),
        },
    },
    OSFMAP.funder: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Funder', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('funder', language_tag='en'),
        },
    },
    OSFMAP.keyword: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Tag', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('keyword', language_tag='en'),
        },
    },
    OWL.sameAs: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('sameAs', language_tag='en'),
        },
    },
    DCTERMS.date: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Date', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('date', language_tag='en'),
        },
    },
    DCTERMS.available: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Date available', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('dateAvailable', language_tag='en'),
        },
    },
    DCTERMS.dateCopyrighted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Date copyrighted', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('dateCopyrighted', language_tag='en'),
        },
    },
    DCTERMS.created: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Date created', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('dateCreated', language_tag='en'),
        },
    },
    DCTERMS.modified: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Date modified', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('dateModified', language_tag='en'),
        },
    },
    DCTERMS.dateSubmitted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Date submitted', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('dateSubmitted', language_tag='en'),
        },
    },
    DCTERMS.dateAccepted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Date accepted', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('dateAccepted', language_tag='en'),
        },
    },
    OSFMAP.dateWithdrawn: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Date withdrawn', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('dateWithdrawn', language_tag='en'),
        },
    },
    OSFMAP.isContainedBy: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Is contained by', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('isContainedBy', language_tag='en'),
        },
    },
    DCTERMS.hasPart: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Has component', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasPart', language_tag='en'),
        },
    },
    DCTERMS.isPartOf: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Is component of', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('isPartOf', language_tag='en'),
        },
    },
    OSFMAP.hasRoot: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Has root', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasRoot', language_tag='en'),
        },
    },
    DCTERMS.references: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('References', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('references', language_tag='en'),
        },
    },
    DCTERMS.hasVersion: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Has version', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasVersion', language_tag='en'),
        },
    },
    DCTERMS.isVersionOf: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Is version of', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('isVersionOf', language_tag='en'),
        },
    },
    OSFMAP.supplements: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Associated preprint', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('supplements', language_tag='en'),
        },
    },
    OSFMAP.isSupplementedBy: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Supplemental materials', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('isSupplementedBy', language_tag='en'),
        },
    },
    OSFMAP.archivedAt: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Archived at', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('archivedAt', language_tag='en'),
        },
    },
    OSFMAP.hasAnalyticCodeResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Analytic code', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasAnalyticCodeResource', language_tag='en'),
        },
    },
    OSFMAP.hasDataResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Data', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasDataResource', language_tag='en'),
        },
    },
    OSFMAP.hasMaterialsResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Materials', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasMaterialsResource', language_tag='en'),
        },
    },
    OSFMAP.hasPapersResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Papers', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasPapersResource', language_tag='en'),
        },
    },
    OSFMAP.hasSupplementalResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Supplemental resource', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasSupplementalResource', language_tag='en'),
        },
    },
    OSFMAP.hasPreregisteredAnalysisPlan: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Preregistered analysis plan', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasPreregisteredAnalysisPlan', language_tag='en'),
        },
    },
    OSFMAP.hasPreregisteredStudyDesign: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Preregistered study design', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('hasPreregisteredStudyDesign', language_tag='en'),
        },
    },
    OSFMAP.omits: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Omits metadata', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('omits', language_tag='en'),
        },
    },
    FOAF.name: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Name', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('name', language_tag='en'),
        },
    },
    OSFMAP.funderIdentifierType: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('funderIdentifierType', language_tag='en'),
        },
    },
    OSFMAP.awardNumber: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Award number', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('awardNumber', language_tag='en'),
        },
    },
    OSFMAP.fileName: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('File name', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('fileName', language_tag='en'),
        },
    },
    OSFMAP.filePath: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('File path', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('filePath', language_tag='en'),
        },
    },
    OSFMAP.format: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Media type', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('mediaType', language_tag='en'),
        },
    },
    OSFMAP.versionNumber: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Version number', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('versionNumber', language_tag='en'),
        },
    },
    OSFMAP.omittedMetadataProperty: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Omitted property', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('omittedMetadataProperty', language_tag='en'),
        },
    },
    DCTERMS.conformsTo: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Registration template', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('conformsTo', language_tag='en'),
        },
    },
    OSFMAP.statedConflictOfInterest: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Stated conflict of interest', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('statedConflictOfInterest', language_tag='en'),
        },
    },
    OSFMAP.isPartOfCollection: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Is part of collection', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('isPartOfCollection', language_tag='en'),
        },
    },
    SKOS.prefLabel: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('prefLabel', language_tag='en'),
        },
    },
    SKOS.altLabel: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('altLabel', language_tag='en'),
        },
    },
    SKOS.inScheme: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('inScheme', language_tag='en'),
        },
    },
    SKOS.broader: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('broader', language_tag='en'),
        },
    },
    DCAT.accessService: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('accessService', language_tag='en'),
        },
    },
    RDFS.label: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Label', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('displayLabel', language_tag='en'),
        },
    },
    JSONAPI_MEMBERNAME: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('JSON:API member name', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('shortFormLabel', language_tag='en'),
        },
    },

    ###
    # types:
    OSFMAP.Project: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Project', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('Project', language_tag='en'),
        },
    },
    OSFMAP.ProjectComponent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Project component', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('ProjectComponent', language_tag='en'),
        },
    },
    OSFMAP.Registration: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Registration', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('Registration', language_tag='en'),
        },
    },
    OSFMAP.RegistrationComponent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Registration component', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('RegistrationComponent', language_tag='en'),
        },
    },
    OSFMAP.Preprint: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Preprint', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('Preprint', language_tag='en'),
        },
    },
    OSFMAP.File: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('File', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('File', language_tag='en'),
        },
    },
    DCTERMS.Agent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Agent', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('Agent', language_tag='en'),
        },
    },
    OSFMAP.FundingAward: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Funding award', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('FundingAward', language_tag='en'),
        },
    },
    OSFMAP.FileVersion: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('File version', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('FileVersion', language_tag='en'),
        },
    },
    OSFMAP.OmittedMetadata: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Omitted metadata', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('OmittedMetadata', language_tag='en'),
        },
    },
    FOAF.Person: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Person', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('Person', language_tag='en'),
        },
    },
    FOAF.Organization: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Organization', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('Organization', language_tag='en'),
        },
    },
    RDF.Property: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Property', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('Property', language_tag='en'),
        },
    },
    DCMITYPE.Collection: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Collection', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('Collection', language_tag='en'),
        },
    },
    SKOS.Concept: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            primitive_rdf.datum('Subject', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('Concept', language_tag='en'),
        },
    },

    ###
    # values:
    OSFMAP['no-conflict-of-interest']: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            primitive_rdf.datum('Creator asserts no conflict of interest.', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            primitive_rdf.datum('no-conflict-of-interest', language_tag='en'),
        },
    },
}


OSFMAP_NORMS = gather.GatheringNorms(
    namestory=(
        primitive_rdf.datum('OSFMAP', language_tag='en'),
        primitive_rdf.datum('OSF Metadata Application Profile', language_tag='en'),
        primitive_rdf.datum('Open Science Framework Metadata Application Profile', language_tag='en'),
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
    (DCTERMS.creator, OSFMAP.affiliation),
    (OSFMAP.hasDataResource,),
    (OSFMAP.hasPreregisteredAnalysisPlan,),
    (OSFMAP.hasPreregisteredStudyDesign,),
    (OSFMAP.isSupplementedBy,),
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


SUGGESTED_PRESENCE_PROPERTIES = frozenset((
    OSFMAP.hasAnalyticCodeResource,
    OSFMAP.hasDataResource,
    OSFMAP.hasMaterialsResource,
    OSFMAP.hasPapersResource,
    OSFMAP.hasPreregisteredAnalysisPlan,
    OSFMAP.hasPreregisteredStudyDesign,
    OSFMAP.hasSupplementalResource,
    OSFMAP.isSupplementedBy,
    OSFMAP.supplements,
))


DATE_PROPERTIES = frozenset((
    DCTERMS.date,
    DCTERMS.available,
    DCTERMS.created,
    DCTERMS.modified,
    DCTERMS.dateCopyrighted,
    DCTERMS.dateSubmitted,
    DCTERMS.dateAccepted,
    OSFMAP.dateWithdrawn,
))


def suggested_property_paths(type_iris: set[str]) -> tuple[tuple[str, ...]]:
    if not type_iris or not type_iris.issubset(OSFMAP_NORMS.focustype_iris):
        _suggested = ()
    elif type_iris == {DCTERMS.Agent}:
        _suggested = AGENT_SUGGESTED_PROPERTY_PATHS
    elif type_iris == {OSFMAP.Preprint}:
        _suggested = PREPRINT_SUGGESTED_PROPERTY_PATHS
    elif type_iris == {OSFMAP.File}:
        _suggested = FILE_SUGGESTED_PROPERTY_PATHS
    elif type_iris <= {OSFMAP.Project, OSFMAP.ProjectComponent}:
        _suggested = PROJECT_SUGGESTED_PROPERTY_PATHS
    elif type_iris <= {OSFMAP.Registration, OSFMAP.RegistrationComponent}:
        _suggested = REGISTRATION_SUGGESTED_PROPERTY_PATHS
    else:
        _suggested = ALL_SUGGESTED_PROPERTY_PATHS
    if FeatureFlag.objects.flag_is_up(FeatureFlag.SUGGEST_CREATOR_FACET):
        return ((DCTERMS.creator,), *_suggested)
    return _suggested


def suggested_filter_operator(property_iri: str):
    # return iri value for the suggested trove-search filter operator
    if is_date_property(property_iri):
        return TROVE['at-date']
    if property_iri in SUGGESTED_PRESENCE_PROPERTIES:
        return TROVE['is-present']
    return TROVE['any-of']


def is_date_property(property_iri):
    # TODO: better inference (rdfs:range?)
    return property_iri in DATE_PROPERTIES
