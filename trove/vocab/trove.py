from django.conf import settings
import gather

from share.util.rdfutil import IriLabeler


###
# an iri namespace for troves of metadata
TROVE = gather.IriNamespace('https://share.osf.io/vocab/trove/')

# a namespace for indexcard iris
TROVE_INDEXCARD = gather.IriNamespace(f'{settings.SHARE_API_URL}trove/index-card/')

# using linked anchors on the jsonapi spec as iris (probably fine)
JSONAPI = gather.IriNamespace('https://jsonapi.org/format/1.1/#')
JSONAPI_MEMBERNAME = JSONAPI['document-member-names']
JSONAPI_RELATIONSHIP = JSONAPI['document-resource-object-relationships']
JSONAPI_ATTRIBUTE = JSONAPI['document-resource-object-attributes']


# some assumed-safe assumptions for iris in trovespace:
# - a name ending in forward slash (`/`) is a namespace
# - an iri fragment (after `#`) is a `,`-separated list
#   of iris; a path of predicates from the root of that
#   index card (for the iri with `#` and after removed)
# - TODO: each iri is an irL that resolves to rdf, html

TROVE_VOCAB: gather.RdfTripleDictionary = {

    # types:
    TROVE.Card: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-card', language_tag='en'),
        },
    },
    TROVE.Cardsearch: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-card-search', language_tag='en'),
        },
    },
    TROVE.Propertysearch: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-property-search', language_tag='en'),
        },
    },
    TROVE.Valuesearch: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-value-search', language_tag='en'),
        },
    },
    TROVE.SearchResult: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('search-result', language_tag='en'),
        },
    },
    TROVE.TextMatchEvidence: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('TextMatchEvidence', language_tag='en'),
        },
    },
    TROVE.IriMatchEvidence: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('IriMatchEvidence', language_tag='en'),
        },
    },

    # attributes:
    TROVE.totalResultCount: {
        gather.RDF.type: {gather.RDF.Property, gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('totalResultCount', language_tag='en'),
        },
    },
    TROVE.cardsearchText: {
        gather.RDF.type: {gather.RDF.Property, gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('cardSearchText', language_tag='en'),
        },
    },
    TROVE.propertysearchText: {
        gather.RDF.type: {gather.RDF.Property, gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('propertySearchText', language_tag='en'),
        },
    },
    TROVE.valuesearchText: {
        gather.RDF.type: {gather.RDF.Property, gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('valueSearchText', language_tag='en'),
        },
    },
    TROVE.cardsearchFilter: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('cardSearchFilter', language_tag='en'),
        },
    },
    TROVE.propertysearchFilter: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('propertySearchFilter', language_tag='en'),
        },
    },
    TROVE.valuesearchFilter: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('valueSearchFilter', language_tag='en'),
        },
    },
    TROVE.matchEvidence: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('matchEvidence', language_tag='en'),
        },
    },
    TROVE.resourceIdentifier: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('resourceIdentifier', language_tag='en'),
        },
    },
    TROVE.resourceMetadata: {
        gather.RDF.type: {gather.RDF.Property, gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('resourceMetadata', language_tag='en'),
        },
    },
    TROVE.matchingHighlight: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('matchingHighlight', language_tag='en'),
        },
    },
    TROVE.propertyPath: {
        gather.RDF.type: {gather.RDF.Property, gather.OWL.FunctionalProperty},
        JSONAPI_MEMBERNAME: {
            gather.text('propertyPath', language_tag='en'),
        },
    },
    TROVE.filterType: {
        gather.RDF.type: {gather.RDF.Property, gather.OWL.FunctionalProperty},
        JSONAPI_MEMBERNAME: {
            gather.text('filterType', language_tag='en'),
        },
    },
    TROVE.filterValue: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('filterValue', language_tag='en'),
        },
    },

    # relationships:
    TROVE.searchResult: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('searchResultPage', language_tag='en'),
        },
    },
    TROVE.evidenceCard: {
        gather.RDF.type: {gather.RDF.Property, gather.OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('evidenceCard', language_tag='en'),
        },
    },
    TROVE.relatedPropertysearch: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('relatedPropertySearch', language_tag='en'),
        },
    },
    TROVE.indexCard: {
        gather.RDF.type: {gather.RDF.Property, gather.OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('indexCard', language_tag='en'),
        },
    },

    # values:
    TROVE['ten-thousands-and-more']: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('ten-thousands-and-more', language_tag='en'),
        },
    },
    TROVE['any-of']: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('any-of', language_tag='en'),
        },
    },
    TROVE['none-of']: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('none-of', language_tag='en'),
        },
    },
    TROVE.before: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('before', language_tag='en'),
        },
    },
    TROVE.after: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('after', language_tag='en'),
        },
    },
}

trove_labeler = IriLabeler(TROVE_VOCAB, label_iri=JSONAPI_MEMBERNAME)
