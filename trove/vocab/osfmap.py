from __future__ import annotations
import typing
import functools
if typing.TYPE_CHECKING:
    from collections.abc import Iterator

from primitive_metadata.primitive_rdf import (
    literal,
    RdfTripleDictionary,
    IriShorthand,
)
from primitive_metadata import gather

from share.models.feature_flag import FeatureFlag
from trove.util.propertypath import (
    Propertypath,
    PropertypathSet,
    parse_propertypath,
    propertypath_key,
)
from trove.util.queryparams import (
    join_queryparam_value,
    split_queryparam_value,
)
from trove.util.shorthand import build_shorthand_from_thesaurus
from trove.vocab.jsonapi import JSONAPI_MEMBERNAME
from trove.vocab.namespaces import (
    DCAT,
    DCTYPE,
    DCTERMS,
    FOAF,
    OSFMAP,
    OWL,
    PROV,
    RDF,
    RDFS,
    SKOS,
    TROVE,
    namespaces_shorthand,
)

OSFMAP_LINK = 'https://osf.io/8yczr'

# TODO: define as turtle, load in trove.vocab.__init__?
OSFMAP_THESAURUS: RdfTripleDictionary = {
    ###
    # properties:
    DCTERMS.identifier: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Identifier', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('identifier', language='en'),
        },
    },
    DCTERMS.creator: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Creator', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('creator', language='en'),
        },
    },
    DCTERMS.title: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Title', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('title', language='en'),
        },
    },
    DCTERMS.publisher: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Provider', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('publisher', language='en'),
        },
    },
    DCTERMS.subject: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Subject', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('subject', language='en'),
        },
    },
    DCTERMS.contributor: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Contributor', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('contributor', language='en'),
        },
    },
    DCTERMS.language: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Language', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('language', language='en'),
        },
    },
    RDF.type: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('resourceType', language='en'),
        },
    },
    DCTERMS.type: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Resource type', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('resourceNature', language='en'),
        },
    },
    DCTERMS.rights: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('License', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('rights', language='en'),
        },
    },
    DCTERMS.rightsHolder: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('License holder', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('rightsHolder', language='en'),
        },
    },
    DCTERMS.description: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Description', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('description', language='en'),
        },
    },
    OSFMAP.affiliation: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Institution', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('affiliation', language='en'),
        },
        DCTERMS.description: {
            literal(
                'Please select an institution to apply to your search. Only OSF Institutions member affiliations are discoverable.',
                language='en')
        },
        OSFMAP.linkText: {
            literal('Learn more about OSF Institutions.', language='en')
        },
        OSFMAP.link: {
            literal('https://www.cos.io/products/osf-institutions', language='en')
        },
    },
    OSFMAP.hasFunding: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Funding award', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasFunding', language='en'),
        },
    },
    OSFMAP.funder: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Funder', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('funder', language='en'),
        },
    },
    OSFMAP.keyword: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Tag', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('keyword', language='en'),
        },
    },
    OWL.sameAs: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('sameAs', language='en'),
        },
    },
    DCTERMS.date: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('date', language='en'),
        },
    },
    DCTERMS.available: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date available', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateAvailable', language='en'),
        },
    },
    DCTERMS.dateCopyrighted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date copyrighted', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateCopyrighted', language='en'),
        },
    },
    DCTERMS.created: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date created', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateCreated', language='en'),
        },
    },
    DCTERMS.modified: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date modified', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateModified', language='en'),
        },
    },
    DCTERMS.dateSubmitted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date submitted', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateSubmitted', language='en'),
        },
    },
    DCTERMS.dateAccepted: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date accepted', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateAccepted', language='en'),
        },
    },
    OSFMAP.dateWithdrawn: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Date withdrawn', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('dateWithdrawn', language='en'),
        },
    },
    OSFMAP.isContainedBy: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Is contained by', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('isContainedBy', language='en'),
        },
    },
    DCTERMS.hasPart: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Has component', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasPart', language='en'),
        },
    },
    DCTERMS.isPartOf: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Is component of', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('isPartOf', language='en'),
        },
    },
    OSFMAP.hasRoot: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Has root', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasRoot', language='en'),
        },
    },
    DCTERMS.references: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('References', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('references', language='en'),
        },
    },
    DCTERMS.hasVersion: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Has version', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasVersion', language='en'),
        },
    },
    DCTERMS.isVersionOf: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Is version of', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('isVersionOf', language='en'),
        },
    },
    OSFMAP.supplements: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Associated preprint', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('supplements', language='en'),
        },
    },
    OSFMAP.isSupplementedBy: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Supplemental materials', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('isSupplementedBy', language='en'),
        },
    },
    OSFMAP.verifiedLink: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Verified Links', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('verifiedLink', language='en'),
        },
    },
    OSFMAP.archivedAt: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Archived at', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('archivedAt', language='en'),
        },
    },
    OSFMAP.hasAnalyticCodeResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Analytic code', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasAnalyticCodeResource', language='en'),
        },
    },
    OSFMAP.hasDataResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Data', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasDataResource', language='en'),
        },
    },
    OSFMAP.hasMaterialsResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Materials', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasMaterialsResource', language='en'),
        },
    },
    OSFMAP.hasPapersResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Papers', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasPapersResource', language='en'),
        },
    },
    OSFMAP.hasSupplementalResource: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Supplemental resource', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasSupplementalResource', language='en'),
        },
    },
    OSFMAP.hasPreregisteredAnalysisPlan: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Preregistered analysis plan', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasPreregisteredAnalysisPlan', language='en'),
        },
    },
    OSFMAP.hasPreregisteredStudyDesign: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Preregistered study design', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasPreregisteredStudyDesign', language='en'),
        },
    },
    OSFMAP.omits: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Omits metadata', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('omits', language='en'),
        },
    },
    FOAF.name: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Name', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('name', language='en'),
        },
    },
    OSFMAP.funderIdentifierType: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('funderIdentifierType', language='en'),
        },
    },
    OSFMAP.awardNumber: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Award number', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('awardNumber', language='en'),
        },
    },
    OSFMAP.fileName: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('File name', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('fileName', language='en'),
        },
    },
    OSFMAP.filePath: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('File path', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('filePath', language='en'),
        },
    },
    OSFMAP.format: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Media type', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('mediaType', language='en'),
        },
    },
    OSFMAP.versionNumber: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Version number', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('versionNumber', language='en'),
        },
    },
    OSFMAP.omittedMetadataProperty: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Omitted property', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('omittedMetadataProperty', language='en'),
        },
    },
    DCTERMS.conformsTo: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Registration template', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('conformsTo', language='en'),
        },
    },
    OSFMAP.statedConflictOfInterest: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Stated conflict of interest', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('statedConflictOfInterest', language='en'),
        },
    },
    OSFMAP.isPartOfCollection: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Is part of collection', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('isPartOfCollection', language='en'),
        },
    },
    SKOS.prefLabel: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('prefLabel', language='en'),
        },
    },
    SKOS.altLabel: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('altLabel', language='en'),
        },
    },
    SKOS.inScheme: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('inScheme', language='en'),
        },
    },
    SKOS.broader: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('broader', language='en'),
        },
    },
    DCAT.accessService: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('accessService', language='en'),
        },
    },
    DCAT.accessURL: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('accessURL', language='en'),
        },
    },
    OSFMAP.hostingInstitution: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('hostingInstitution', language='en'),
        },
    },
    PROV.qualifiedAttribution: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('qualifiedAttribution', language='en')},
    },
    PROV.agent: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('agent', language='en')},
    },
    DCAT.hadRole: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('hadRole', language='en')},
    },
    OSFMAP.usage: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('usage', language='en')},
    },
    OSFMAP.storageRegion: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('storageRegion', language='en')},
    },
    OSFMAP.storageByteCount: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('storageByteCount', language='en')},
    },
    OSFMAP.hasOsfAddon: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('hasOsfAddon', language='en')},
    },
    OSFMAP.viewCount: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('viewCount', language='en')},
    },
    OSFMAP.viewSessionCount: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('viewSessionCount', language='en')},
    },
    OSFMAP.downloadCount: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('downloadCount', language='en')},
    },
    OSFMAP.downloadSessionCount: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('downloadSessionCount', language='en')},
    },
    DCTERMS.temporal: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('temporalCoverage', language='en')},
    },
    RDFS.label: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Label', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('displayLabel', language='en'),
        },
    },
    JSONAPI_MEMBERNAME: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('JSON:API member name', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('shortFormLabel', language='en'),
        },
    },
    OSFMAP.linkText: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('linkText', language='en'),
        },
    },
    OSFMAP.link: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            literal('link', language='en'),
        },
    },

    ###
    # types:
    OSFMAP.Project: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Project', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Project', language='en'),
        },
    },
    OSFMAP.ProjectComponent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Project component', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('ProjectComponent', language='en'),
        },
    },
    OSFMAP.Registration: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Registration', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Registration', language='en'),
        },
    },
    OSFMAP.RegistrationComponent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Registration component', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('RegistrationComponent', language='en'),
        },
    },
    OSFMAP.Preprint: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Preprint', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Preprint', language='en'),
        },
    },
    OSFMAP.File: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('File', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('File', language='en'),
        },
    },
    DCTERMS.Agent: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Agent', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Agent', language='en'),
        },
    },
    OSFMAP.FundingAward: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Funding award', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('FundingAward', language='en'),
        },
    },
    OSFMAP.FileVersion: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('File version', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('FileVersion', language='en'),
        },
    },
    OSFMAP.OmittedMetadata: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Omitted metadata', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('OmittedMetadata', language='en'),
        },
    },
    FOAF.Person: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Person', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Person', language='en'),
        },
    },
    FOAF.Organization: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Organization', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Organization', language='en'),
        },
    },
    RDF.Property: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Property', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Property', language='en'),
        },
    },
    DCTYPE.Collection: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Collection', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Collection', language='en'),
        },
    },
    SKOS.Concept: {
        RDF.type: {RDFS.Class},
        RDFS.label: {
            literal('Subject', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('Concept', language='en'),
        },
    },
    OSFMAP.hasCedarTemplate: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Includes community schema', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('hasCedarTemplate', language='en'),
        },
    },

    ###
    # values:
    OSFMAP['no-conflict-of-interest']: {
        RDF.type: {RDF.Property},
        RDFS.label: {
            literal('Creator asserts no conflict of interest.', language='en'),
        },
        JSONAPI_MEMBERNAME: {
            literal('no-conflict-of-interest', language='en'),
        },
    },
    # filter-operator values from `trove.vocab.trove.TROVE_API_THESAURUS`
    # duplicated here so `osfmap_json_shorthand` does not prefix "trove:"
    TROVE['any-of']: {
        JSONAPI_MEMBERNAME: {literal('any-of', language='en')},
    },
    TROVE['none-of']: {
        JSONAPI_MEMBERNAME: {literal('none-of', language='en')},
    },
    TROVE['is-absent']: {
        JSONAPI_MEMBERNAME: {literal('is-absent', language='en')},
    },
    TROVE['is-present']: {
        JSONAPI_MEMBERNAME: {literal('is-present', language='en')},
    },
    TROVE.before: {
        JSONAPI_MEMBERNAME: {literal('before', language='en')},
    },
    TROVE.after: {
        JSONAPI_MEMBERNAME: {literal('after', language='en')},
    },
}


OSFMAP_NORMS = gather.GatheringNorms.new(
    namestory=(
        literal('OSFMAP', language='en'),
        literal('OSF Metadata Application Profile', language='en'),
        literal('Open Science Framework Metadata Application Profile', language='en'),
    ),
    thesaurus=OSFMAP_THESAURUS,
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
    (DCTERMS.subject,),
    (DCTERMS.rights,),
    (DCTERMS.type,),
    (OSFMAP.affiliation,),
    (OSFMAP.isPartOfCollection,),
    (OSFMAP.supplements,),
    (OSFMAP.hasCedarTemplate,),
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
    (OSFMAP.hasCedarTemplate,),
)


PREPRINT_SUGGESTED_PROPERTY_PATHS = (
    (DCTERMS.created,),
    (DCTERMS.subject,),
    (DCTERMS.rights,),
    (DCTERMS.publisher,),
    (OSFMAP.affiliation,),
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
    (OSFMAP.hasCedarTemplate,),
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


TITLE_PROPERTIES = (DCTERMS.title,)
NAME_PROPERTIES = (FOAF.name, OSFMAP.fileName)
LABEL_PROPERTIES = (RDFS.label, SKOS.prefLabel, SKOS.altLabel)
NAMELIKE_PROPERTIES = (*TITLE_PROPERTIES, *NAME_PROPERTIES, *LABEL_PROPERTIES)
SKIPPABLE_PROPERTIES = (OSFMAP.contains, OWL.sameAs)
EXTRA_INDEXED_LITERAL_PATHS = frozenset((
    # indirect text-search paths used by osf-search
    (DCTERMS.creator, FOAF.name),
    (OSFMAP.isContainedBy, DCTERMS.creator, FOAF.name),
))

DEFAULT_TABULAR_SEARCH_COLUMN_PATHS: tuple[tuple[str, ...], ...] = (
    (OWL.sameAs,),  # includes DOI
    (RDF.type,),
    (DCTERMS.type,),
    (DCTERMS.title,),
    (FOAF.name,),
    (DCTERMS.created,),
    (DCTERMS.modified,),
    (DCTERMS.rights,),
)

# end constants
###


###
# functions

@functools.cache  # built once
def osfmap_json_shorthand() -> IriShorthand:
    '''build iri shorthand that includes unprefixed osfmap terms
    '''
    return build_shorthand_from_thesaurus(
        thesaurus=OSFMAP_THESAURUS,
        label_predicate=JSONAPI_MEMBERNAME,
        base_shorthand=namespaces_shorthand(),
    )


def parse_osfmap_propertypath(serialized_path: str, *, allow_globs=False) -> Propertypath:
    return parse_propertypath(serialized_path, osfmap_json_shorthand(), allow_globs=allow_globs)


def parse_osfmap_propertypath_set(serialized_path_set: str, *, allow_globs=False) -> Iterator[Propertypath]:
    for _path in split_queryparam_value(serialized_path_set):
        yield parse_osfmap_propertypath(_path, allow_globs=allow_globs)


def osfmap_propertypath_key(propertypath: Propertypath) -> str:
    return propertypath_key(propertypath, osfmap_json_shorthand())


def osfmap_propertypath_set_key(propertypath_set: PropertypathSet) -> str:
    return join_queryparam_value(
        osfmap_propertypath_key(_propertypath)
        for _propertypath in propertypath_set
    )


def suggested_property_paths(type_iris: set[str]) -> tuple[tuple[str, ...], ...]:
    _suggested: tuple[tuple[str, ...], ...]
    if not type_iris or not type_iris.issubset(OSFMAP_NORMS.focustype_iris):
        _suggested = ()
    elif type_iris == {DCTERMS.Agent}:
        _suggested = AGENT_SUGGESTED_PROPERTY_PATHS
    elif type_iris == {OSFMAP.Preprint}:
        _suggested = PREPRINT_SUGGESTED_PROPERTY_PATHS
        if not FeatureFlag.objects.flag_is_up(FeatureFlag.PREPRINT_AFFILIATIONS):
            # replace `affilation` with `creator.affiliation`
            _no = (OSFMAP.affiliation,)
            _instead = (DCTERMS.creator, OSFMAP.affiliation)
            _suggested = tuple(
                (_instead if (_path == _no) else _path)
                for _path in _suggested
            )
    elif type_iris == {OSFMAP.File}:
        _suggested = FILE_SUGGESTED_PROPERTY_PATHS
    elif type_iris <= {OSFMAP.Project, OSFMAP.ProjectComponent}:
        _suggested = PROJECT_SUGGESTED_PROPERTY_PATHS
    elif type_iris <= {OSFMAP.Registration, OSFMAP.RegistrationComponent}:
        _suggested = REGISTRATION_SUGGESTED_PROPERTY_PATHS
    else:
        _suggested = ALL_SUGGESTED_PROPERTY_PATHS
    if _suggested and FeatureFlag.objects.flag_is_up(FeatureFlag.SUGGEST_CREATOR_FACET):
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
