from primitive_metadata.primitive_rdf import (
    literal,
    RdfTripleDictionary,
)
from primitive_metadata import gather

from share.models.feature_flag import FeatureFlag
from trove.util.iri_labeler import IriLabeler
from trove.vocab.jsonapi import JSONAPI_MEMBERNAME
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
OSFMAP_VOCAB: RdfTripleDictionary = {
    ###
    # properties:
    DCTERMS.identifier: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Identifier', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('identifier', language_tag='en'),
        },
    },
    DCTERMS.creator: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Creator', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('creator', language_tag='en'),
        },
    },
    DCTERMS.title: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Title', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('title', language_tag='en'),
        },
    },
    DCTERMS.publisher: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Provider', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('publisher', language_tag='en'),
        },
    },
    DCTERMS.subject: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Subject', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('subject', language_tag='en'),
        },
    },
    DCTERMS.contributor: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Contributor', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('contributor', language_tag='en'),
        },
    },
    DCTERMS.language: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Language', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('language', language_tag='en'),
        },
    },
    RDF.type: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('resourceType', language_tag='en'),
        },
    },
    DCTERMS.type: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Resource type', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('resourceNature', language_tag='en'),
        },
    },
    DCTERMS.rights: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('License', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('rights', language_tag='en'),
        },
    },
    DCTERMS.rightsHolder: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('License holder', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('rightsHolder', language_tag='en'),
        },
    },
    DCTERMS.description: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Description', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('description', language_tag='en'),
        },
    },
    OSFMAP.affiliation: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Institution', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('affiliation', language_tag='en'),
        },
    },
    OSFMAP.hasFunding: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Funding award', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasFunding', language_tag='en'),
        },
    },
    OSFMAP.funder: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Funder', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('funder', language_tag='en'),
        },
    },
    OSFMAP.keyword: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Tag', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('keyword', language_tag='en'),
        },
    },
    OWL.sameAs: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('sameAs', language_tag='en'),
        },
    },
    DCTERMS.date: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('date', language_tag='en'),
        },
    },
    DCTERMS.available: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date available', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateAvailable', language_tag='en'),
        },
    },
    DCTERMS.dateCopyrighted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date copyrighted', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateCopyrighted', language_tag='en'),
        },
    },
    DCTERMS.created: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date created', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateCreated', language_tag='en'),
        },
    },
    DCTERMS.modified: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date modified', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateModified', language_tag='en'),
        },
    },
    DCTERMS.dateSubmitted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date submitted', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateSubmitted', language_tag='en'),
        },
    },
    DCTERMS.dateAccepted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date accepted', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateAccepted', language_tag='en'),
        },
    },
    OSFMAP.dateWithdrawn: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date withdrawn', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateWithdrawn', language_tag='en'),
        },
    },
    OSFMAP.isContainedBy: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Is contained by', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('isContainedBy', language_tag='en'),
        },
    },
    DCTERMS.hasPart: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Has component', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasPart', language_tag='en'),
        },
    },
    DCTERMS.isPartOf: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Is component of', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('isPartOf', language_tag='en'),
        },
    },
    OSFMAP.hasRoot: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Has root', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasRoot', language_tag='en'),
        },
    },
    DCTERMS.references: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('References', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('references', language_tag='en'),
        },
    },
    DCTERMS.hasVersion: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Has version', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasVersion', language_tag='en'),
        },
    },
    DCTERMS.isVersionOf: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Is version of', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('isVersionOf', language_tag='en'),
        },
    },
    OSFMAP.supplements: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Associated preprint', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('supplements', language_tag='en'),
        },
    },
    OSFMAP.isSupplementedBy: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Supplemental materials', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('isSupplementedBy', language_tag='en'),
        },
    },
    OSFMAP.archivedAt: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Archived at', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('archivedAt', language_tag='en'),
        },
    },
    OSFMAP.hasAnalyticCodeResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Analytic code', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasAnalyticCodeResource', language_tag='en'),
        },
    },
    OSFMAP.hasDataResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Data', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasDataResource', language_tag='en'),
        },
    },
    OSFMAP.hasMaterialsResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Materials', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasMaterialsResource', language_tag='en'),
        },
    },
    OSFMAP.hasPapersResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Papers', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasPapersResource', language_tag='en'),
        },
    },
    OSFMAP.hasSupplementalResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Supplemental resource', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasSupplementalResource', language_tag='en'),
        },
    },
    OSFMAP.hasPreregisteredAnalysisPlan: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Preregistered analysis plan', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasPreregisteredAnalysisPlan', language_tag='en'),
        },
    },
    OSFMAP.hasPreregisteredStudyDesign: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Preregistered study design', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasPreregisteredStudyDesign', language_tag='en'),
        },
    },
    OSFMAP.omits: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Omits metadata', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('omits', language_tag='en'),
        },
    },
    FOAF.name: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Name', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('name', language_tag='en'),
        },
    },
    OSFMAP.funderIdentifierType: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('funderIdentifierType', language_tag='en'),
        },
    },
    OSFMAP.awardNumber: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Award number', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('awardNumber', language_tag='en'),
        },
    },
    OSFMAP.fileName: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('File name', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('fileName', language_tag='en'),
        },
    },
    OSFMAP.filePath: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('File path', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('filePath', language_tag='en'),
        },
    },
    OSFMAP.format: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Media type', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('mediaType', language_tag='en'),
        },
    },
    OSFMAP.versionNumber: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Version number', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('versionNumber', language_tag='en'),
        },
    },
    OSFMAP.omittedMetadataProperty: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Omitted property', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('omittedMetadataProperty', language_tag='en'),
        },
    },
    DCTERMS.conformsTo: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Registration template', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('conformsTo', language_tag='en'),
        },
    },
    OSFMAP.statedConflictOfInterest: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Stated conflict of interest', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('statedConflictOfInterest', language_tag='en'),
        },
    },
    OSFMAP.isPartOfCollection: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Is part of collection', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('isPartOfCollection', language_tag='en'),
        },
    },
    SKOS.prefLabel: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('prefLabel', language_tag='en'),
        },
    },
    SKOS.altLabel: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('altLabel', language_tag='en'),
        },
    },
    SKOS.inScheme: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('inScheme', language_tag='en'),
        },
    },
    SKOS.broader: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('broader', language_tag='en'),
        },
    },
    DCAT.accessService: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('accessService', language_tag='en'),
        },
    },
    RDFS.label: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Label', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('displayLabel', language_tag='en'),
        },
    },
    JSONAPI_MEMBERNAME: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('JSON:API member name', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('shortFormLabel', language_tag='en'),
        },
    },

    ###
    # types:
    OSFMAP.Project: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Project', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Project', language_tag='en'),
        },
    },
    OSFMAP.ProjectComponent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Project component', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('ProjectComponent', language_tag='en'),
        },
    },
    OSFMAP.Registration: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Registration', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Registration', language_tag='en'),
        },
    },
    OSFMAP.RegistrationComponent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Registration component', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('RegistrationComponent', language_tag='en'),
        },
    },
    OSFMAP.Preprint: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Preprint', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Preprint', language_tag='en'),
        },
    },
    OSFMAP.File: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('File', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('File', language_tag='en'),
        },
    },
    DCTERMS.Agent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Agent', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Agent', language_tag='en'),
        },
    },
    OSFMAP.FundingAward: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Funding award', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('FundingAward', language_tag='en'),
        },
    },
    OSFMAP.FileVersion: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('File version', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('FileVersion', language_tag='en'),
        },
    },
    OSFMAP.OmittedMetadata: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Omitted metadata', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('OmittedMetadata', language_tag='en'),
        },
    },
    FOAF.Person: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Person', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Person', language_tag='en'),
        },
    },
    FOAF.Organization: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Organization', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Organization', language_tag='en'),
        },
    },
    RDF.Property: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Property', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Property', language_tag='en'),
        },
    },
    DCMITYPE.Collection: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Collection', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Collection', language_tag='en'),
        },
    },
    SKOS.Concept: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Subject', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Concept', language_tag='en'),
        },
    },

    ###
    # values:
    OSFMAP['no-conflict-of-interest']: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Creator asserts no conflict of interest.', language_tag='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('no-conflict-of-interest', language_tag='en'),
        },
    },
}


OSFMAP_NORMS = gather.GatheringNorms(
    namestory=(
        literal('OSFMAP', language_tag='en'),
        literal('OSF Metadata Application Profile', language_tag='en'),
        literal('Open Science Framework Metadata Application Profile', language_tag='en'),
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
