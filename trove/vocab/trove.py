from django.conf import settings
import gather

from share.util.rdfutil import IriLabeler
from trove.vocab.iri_namespace import TROVE, JSONAPI, RDF, RDFS, OWL


# using linked anchors on the jsonapi spec as iris (probably fine)
JSONAPI_MEMBERNAME = JSONAPI['document-member-names']
JSONAPI_RELATIONSHIP = JSONAPI['document-resource-object-relationships']
JSONAPI_ATTRIBUTE = JSONAPI['document-resource-object-attributes']


# some assumed-safe assumptions for iris in trovespace:
# - a name ending in forward slash (`/`) is a namespace
# - an iri fragment (after `#`) is a `,`-separated list
#   of iris; a path of predicates from the root of that
#   index card (for the iri with `#` and after removed)
# - TODO: each iri is an irL that resolves to rdf, html

TROVE_API_VOCAB: gather.RdfTripleDictionary = {

    # types:
    TROVE.Indexcard: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-card', language_tag='en'),
        },
    },
    TROVE.Cardsearch: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-card-search', language_tag='en'),
        },
    },
    TROVE.Propertysearch: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-property-search', language_tag='en'),
        },
    },
    TROVE.Valuesearch: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-value-search', language_tag='en'),
        },
    },
    TROVE.SearchResult: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('search-result', language_tag='en'),
        },
    },
    TROVE.TextMatchEvidence: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('TextMatchEvidence', language_tag='en'),
        },
    },
    TROVE.IriMatchEvidence: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('IriMatchEvidence', language_tag='en'),
        },
    },

    # attributes:
    TROVE.totalResultCount: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('totalResultCount', language_tag='en'),
        },
    },
    TROVE.cardsearchText: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('cardSearchText', language_tag='en'),
        },
    },
    TROVE.propertysearchText: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('propertySearchText', language_tag='en'),
        },
    },
    TROVE.valuesearchText: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('valueSearchText', language_tag='en'),
        },
    },
    TROVE.cardsearchFilter: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('cardSearchFilter', language_tag='en'),
        },
    },
    TROVE.propertysearchFilter: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('propertySearchFilter', language_tag='en'),
        },
    },
    TROVE.valuesearchFilter: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('valueSearchFilter', language_tag='en'),
        },
    },
    TROVE.matchEvidence: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('matchEvidence', language_tag='en'),
        },
    },
    TROVE.resourceIdentifier: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('resourceIdentifier', language_tag='en'),
        },
    },
    TROVE.resourceMetadata: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('resourceMetadata', language_tag='en'),
        },
    },
    TROVE.matchingHighlight: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('matchingHighlight', language_tag='en'),
        },
    },
    TROVE.propertyPath: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty},
        JSONAPI_MEMBERNAME: {
            gather.text('propertyPath', language_tag='en'),
        },
    },
    TROVE.filterType: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty},
        JSONAPI_MEMBERNAME: {
            gather.text('filterType', language_tag='en'),
        },
    },
    TROVE.filterValue: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('filterValue', language_tag='en'),
        },
    },

    # relationships:
    TROVE.searchResult: {
        RDF.type: {RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('searchResultPage', language_tag='en'),
        },
    },
    TROVE.evidenceCard: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('evidenceCard', language_tag='en'),
        },
    },
    TROVE.relatedPropertysearch: {
        RDF.type: {RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('relatedPropertySearch', language_tag='en'),
        },
    },
    TROVE.indexCard: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('indexCard', language_tag='en'),
        },
    },

    # values:
    TROVE['ten-thousands-and-more']: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('ten-thousands-and-more', language_tag='en'),
        },
    },
    TROVE['any-of']: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('any-of', language_tag='en'),
        },
    },
    TROVE['none-of']: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('none-of', language_tag='en'),
        },
    },
    TROVE.before: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('before', language_tag='en'),
        },
    },
    TROVE.after: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('after', language_tag='en'),
        },
    },
}

trove_labeler = IriLabeler(TROVE_API_VOCAB, label_iri=JSONAPI_MEMBERNAME)


def trove_indexcard_namespace():
    return gather.IriNamespace(f'{settings.SHARE_API_URL}trove/index-card/')


def trove_indexcard_iri(indexcard_uuid):
    return trove_indexcard_namespace()[str(indexcard_uuid)]
