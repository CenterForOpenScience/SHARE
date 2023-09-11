from django.conf import settings
from gather import primitive_rdf

from trove.util.iri_labeler import IriLabeler
from trove.vocab.namespaces import TROVE, JSONAPI, RDF, RDFS, OWL


# using linked anchors on the jsonapi spec as iris (probably fine)
JSONAPI_MEMBERNAME = JSONAPI['document-member-names']
JSONAPI_RELATIONSHIP = JSONAPI['document-resource-object-relationships']
JSONAPI_ATTRIBUTE = JSONAPI['document-resource-object-attributes']
JSONAPI_LINK = JSONAPI['document-links']
JSONAPI_LINK_OBJECT = JSONAPI['document-links-link-object']


# some assumed-safe assumptions for iris in trovespace:
# - a name ending in forward slash (`/`) is a namespace
# - an iri fragment (after `#`) is a `,`-separated list
#   of iris; a path of predicates from the root of that
#   index card (for the iri with `#` and after removed)
# - TODO: each iri is an irL that resolves to rdf, html

TROVE_API_VOCAB: primitive_rdf.RdfTripleDictionary = {

    # types:
    TROVE.Indexcard: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('index-card', language_tag='en'),
        },
    },
    TROVE.Cardsearch: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('index-card-search', language_tag='en'),
        },
    },
    TROVE.Valuesearch: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('index-value-search', language_tag='en'),
        },
    },
    TROVE.SearchResult: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('search-result', language_tag='en'),
        },
    },
    TROVE.RelatedPropertypath: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('related-property-path', language_tag='en'),
        },
    },
    TROVE.TextMatchEvidence: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('TextMatchEvidence', language_tag='en'),
        },
    },
    TROVE.IriMatchEvidence: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('IriMatchEvidence', language_tag='en'),
        },
    },

    # attributes:
    TROVE.totalResultCount: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('totalResultCount', language_tag='en'),
        },
    },
    TROVE.cardsearchText: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('cardSearchText', language_tag='en'),
        },
    },
    TROVE.valuesearchText: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('valueSearchText', language_tag='en'),
        },
    },
    TROVE.cardsearchFilter: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('cardSearchFilter', language_tag='en'),
        },
    },
    TROVE.valuesearchFilter: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('valueSearchFilter', language_tag='en'),
        },
    },
    TROVE.matchEvidence: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('matchEvidence', language_tag='en'),
        },
    },
    TROVE.resourceIdentifier: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('resourceIdentifier', language_tag='en'),
        },
    },
    TROVE.resourceMetadata: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('resourceMetadata', language_tag='en'),
        },
    },
    TROVE.matchingHighlight: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('matchingHighlight', language_tag='en'),
        },
    },
    TROVE.propertyPathKey: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('propertyPathKey', language_tag='en'),
        },
    },
    TROVE.propertyPath: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('propertyPath', language_tag='en'),
        },
    },
    TROVE.osfmapPropertyPath: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('osfmapPropertyPath', language_tag='en'),
        },
    },
    TROVE.propertyPathSet: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('propertyPathSet', language_tag='en'),
        },
    },
    TROVE.osfmapPropertyPathSet: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('osfmapPropertyPathSet', language_tag='en'),
        },
    },
    TROVE.filterType: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('filterType', language_tag='en'),
        },
    },
    TROVE.filterValue: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('filterValueSet', language_tag='en'),
        },
    },
    TROVE.cardsearchResultCount: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('cardSearchResultCount', language_tag='en'),
        },
    },
    TROVE.suggestedFilterOperator: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('suggestedFilterOperator', language_tag='en'),
        },
    },

    # relationships:
    TROVE.searchResultPage: {
        RDF.type: {RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('searchResultPage', language_tag='en'),
        },
    },
    TROVE.evidenceCard: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('evidenceCard', language_tag='en'),
        },
    },
    TROVE.relatedPropertyList: {
        RDF.type: {RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('relatedProperties', language_tag='en'),
        },
    },
    TROVE.indexCard: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('indexCard', language_tag='en'),
        },
    },

    # values:
    TROVE['ten-thousands-and-more']: {
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('ten-thousands-and-more', language_tag='en'),
        },
    },
    TROVE['any-of']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('any-of', language_tag='en'),
        },
    },
    TROVE['none-of']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('none-of', language_tag='en'),
        },
    },
    TROVE['is-absent']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('is-absent', language_tag='en'),
        },
    },
    TROVE['is-present']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('is-present', language_tag='en'),
        },
    },
    TROVE.before: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('before', language_tag='en'),
        },
    },
    TROVE.after: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('after', language_tag='en'),
        },
    },
    TROVE['at-date']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('at-date', language_tag='en'),
        },
    },

    # other:
    RDF.type: {
        JSONAPI_MEMBERNAME: {
            primitive_rdf.text('@type'),
        },
    },
}

trove_labeler = IriLabeler(
    TROVE_API_VOCAB,
    label_iri=JSONAPI_MEMBERNAME,
    acceptable_prefixes=('trove:',),
)


def trove_indexcard_namespace():
    return primitive_rdf.IriNamespace(f'{settings.SHARE_WEB_URL}trove/index-card/')


def trove_indexcard_iri(indexcard_uuid):
    return trove_indexcard_namespace()[str(indexcard_uuid)]
