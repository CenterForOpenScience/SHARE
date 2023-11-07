from django.conf import settings
from primitive_metadata.primitive_rdf import (
    IriNamespace,
    RdfTripleDictionary,
    literal,
    literal_json,
)

from trove.util.iri_labeler import IriLabeler
from trove.vocab.jsonapi import (
    JSONAPI_MEMBERNAME,
    JSONAPI_ATTRIBUTE,
    JSONAPI_RELATIONSHIP,
)
from trove.vocab.osfmap import osfmap_labeler, DATE_PROPERTIES
from trove.vocab.namespaces import TROVE, RDF, RDFS, OWL, DCTERMS


# some assumed-safe assumptions for iris in trovespace:
# - a name ending in forward slash (`/`) is a namespace
# - an iri fragment (after `#`) is a `,`-separated list
#   of iris; a path of predicates from the root of that
#   index card (for the iri with `#` and after removed)
# - TODO: each iri is an irL that resolves to rdf, html

TROVE_API_VOCAB: RdfTripleDictionary = {
    TROVE.API: {
        RDFS.label: {literal('trove: a catalog of metadata cards', language_tag='en')},
        RDFS.comment: {literal('for searching', language_tag='en')},
        TROVE.hasPath: {
            TROVE['path/index-card-search'],
            TROVE['path/index-value-search'],
            TROVE['path/index-card'],
        },
        DCTERMS.description: {literal('''
for searching your trove of metadata on lil index-cards

## terminology

### index-card
an **index-card** is a metadata record focused on a specific thing.

that thing is called the "focus" and is identified by a "focus iri".

the metadata about the thing is a small-ish [rdf graph](https://www.w3.org/TR/rdf11-concepts/#data-model) in which every triple is reachable from the card's focus iri.

note: there is not (yet) any size limit for an index-card's metadata,
but it is intended to be small enough for an old computer to use naively, all at once
(let's start the conversation at 4 KiB -- might be nice to fit in one page of memory)

### property-path
several query param names and values accept a **property-path** (or several), which is a dot-separated path of short-hand IRIs -- currently only supports OSFMAP shorthand (TODO: link), but may eventually support custom IRI shorthand defined in query parameters of the request.

for example, `creator.name` is parsed as a two-step path that follows
`creator` (aka `http://purl.org/dc/terms/creator`) and then `name` (aka `http://xmlns.com/foaf/0.1/name`)

most places that allow one property-path also accept a comma-separated set of paths,
like `title,description` (which is parsed as two paths: `title` and `description`)
or `creator.name,affiliation.name,funder.name` (which is parsed as three paths: `creator.name`,
`affiliation.name`, and `funder.name`)

''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },

    # types:
    TROVE.Indexcard: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('index-card', language_tag='en')},
    },
    TROVE.Cardsearch: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('index-card-search', language_tag='en')},
    },
    TROVE.Valuesearch: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('index-value-search', language_tag='en')},
    },
    TROVE.SearchResult: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('search-result', language_tag='en')},
    },
    TROVE.RelatedPropertypath: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('related-property-path', language_tag='en')},
    },
    TROVE.TextMatchEvidence: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('TextMatchEvidence', language_tag='en')},
    },
    TROVE.IriMatchEvidence: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('IriMatchEvidence', language_tag='en')},
    },

    # paths:
    TROVE['path/index-card-search']: {
        TROVE.iriPath: {literal('/trove/index-card-search')},
        TROVE.hasParameter: {
            TROVE.cardSearchText,
            TROVE.cardSearchFilter,
            TROVE.pageSize,
            TROVE.pageCursor,
            TROVE.sort,
            # TROVE.include,
        },
        RDFS.label: {literal('index-card-search', language_tag='en')},
        RDFS.comment: {literal('search for index-cards based on the metadata they contain', language_tag='en')},
        DCTERMS.description: {literal('''TODO
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },
    TROVE['path/index-value-search']: {
        TROVE.iriPath: {literal('/trove/index-value-search')},
        TROVE.hasParameter: {
            TROVE.valueSearchPropertyPath,
            TROVE.cardSearchText,
            TROVE.cardSearchFilter,
            TROVE.valueSearchText,
            TROVE.valueSearchFilter,
            TROVE.pageSize,
            TROVE.pageCursor,
            TROVE.sort,
            # TROVE.include,
        },
        RDFS.label: {literal('index-value-search', language_tag='en')},
        RDFS.comment: {literal('search for iri values based on how they are used', language_tag='en')},
        DCTERMS.description: {literal('''index-value-search
find IRIs you could use in a cardSearchFilter
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },
    TROVE['path/index-card']: {
        TROVE.iriPath: {literal('/trove/index-card/{indexCardId}')},
        TROVE.hasParameter: {
            TROVE.indexCardId,
        },
        RDFS.label: {literal('get index-card', language_tag='en')},
        RDFS.comment: {literal('get a specific index-card by id', language_tag='en')},
        DCTERMS.description: {literal('''TODO
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },

    # parameters:
    TROVE.cardSearchText: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE, TROVE.QueryParameter},
        JSONAPI_MEMBERNAME: {literal('cardSearchText', language_tag='en')},
        RDFS.label: {literal('cardSearchText', language_tag='en')},
        RDFS.comment: {literal('free-text search query', language_tag='en')},
        TROVE.jsonSchema: {literal_json({'type': 'string'})},
        DCTERMS.description: {literal('''
text query, e.g. `cardSearchText=foo`

special characters in search text:

* `"` (double quotes): use on both sides of a word or phrase to require exact text match
* `-` (hyphen): use before a word or quoted phrase (before the leading `"`)

can specify path(s) to text properties (using osfmap iri shorthand)

* `cardSearchText[title]=...`
* `cardSearchText[creator.name]=...`

the special path segment `*` matches any property

* `cardSearchText[*]=...`: match text values one step away from the focus (default for `cardSearchText=` without `[]`)
* `cardSearchText[*.*]=...`: match text values exactly two steps away
* `cardSearchText[*,*.*]=...`: match text values one OR two steps away
* `cardSearchText[*,creator.name]=...`: match text values one step away OR at the specific path `creator.name`

TODO: support full iris (maybe via `iriShorthand[foo]=...`? or `@context[foo]=...` if `@` )
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },
    TROVE.cardSearchFilter: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE, TROVE.QueryParameter},
        JSONAPI_MEMBERNAME: {literal('cardSearchFilter', language_tag='en')},
        RDFS.label: {literal('cardSearchFilter', language_tag='en')},
        RDFS.comment: {literal('filter to index-cards with specific IRIs at specific locations', language_tag='en')},
        DCTERMS.description: {literal('''
## cardSearchFilter
each query parameter in the *cardSearchFilter* family may exclude index-cards from
the result set based on IRI values at specific locations in the index-card rdf tree.

### propertyPaths
...TODO
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },
    TROVE.valueSearchPropertyPath: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE, TROVE.QueryParameter, TROVE.RequiredParameter},
        JSONAPI_MEMBERNAME: {literal('valueSearchPropertyPath', language_tag='en')},
        RDFS.label: {literal('valueSearchPropertyPath', language_tag='en')},
        RDFS.comment: {literal('the location to look for values in index-cards', language_tag='en')},
        DCTERMS.description: {literal('''
dot-separated path of short-hand IRIs

`valueSearchPropertyPath=creator`
`valueSearchPropertyPath=creator.affiliation`

note: multiple property paths are not supported
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },
    TROVE.valueSearchText: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE, TROVE.QueryParameter},
        RDFS.label: {literal('valueSearchText', language_tag='en')},
        JSONAPI_MEMBERNAME: {literal('valueSearchText', language_tag='en')},
        RDFS.comment: {literal('free-text search (within a title, name, or label associated with an IRI)', language_tag='en')},
        DCTERMS.description: {literal('''
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },
    TROVE.indexCardId: {
        RDF.type: {RDF.Property, TROVE.PathParameter},
        RDFS.label: {literal('indexCardId', language_tag='en')},
        RDFS.comment: {literal('unique identifier for an index-card', language_tag='en')},
        DCTERMS.description: {literal('''TODO
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },
    TROVE.valueSearchFilter: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE, TROVE.QueryParameter},
        JSONAPI_MEMBERNAME: {literal('valueSearchFilter', language_tag='en')},
        RDFS.label: {literal('valueSearchFilter', language_tag='en')},
        RDFS.comment: {literal('filter to values that match a specific IRI or have a specific type', language_tag='en')},
        DCTERMS.description: {literal('''
TODO

only two supported:
`valueSearchFilter[sameAs]=`
`valueSearchFilter[resourceType]=`
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },
    TROVE.pageCursor: {
        RDF.type: {TROVE.QueryParameter},
        RDFS.label: {literal('page[cursor]', language_tag='en')},
        RDFS.comment: {literal('get a specific page by a given cursor', language_tag='en')},
        DCTERMS.description: {literal('''
cursor links are returned by the api and may not be valid forever

may not be used with `page[size]`
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },
    TROVE.pageSize: {
        RDF.type: {TROVE.QueryParameter},
        RDFS.label: {literal('page[size]', language_tag='en')},
        RDFS.comment: {literal('maximum number of search results returned at once', language_tag='en')},
        DCTERMS.description: {literal('''

integer value, e.g. `page[size]=7` (default `13`)

may not be used with `page[cursor]`
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },

    TROVE.sort: {
        RDF.type: {TROVE.QueryParameter},
        RDFS.label: {literal('sort', language_tag='en')},
        RDFS.comment: {literal('how to order search results', language_tag='en')},
        DCTERMS.description: {literal(f'''## sort
given a short-hand iri for a date property, will sort results by that date ascending (earliest first)
-- prefix with `-` to sort descending (latest first)

supported date properties: {", ".join(osfmap_labeler.label_for_iri(_date_iri) for _date_iri in DATE_PROPERTIES)}

by default (or if given `-relevance`), will sort by some notion of relevance to given text parameters

if no text parameters, sorts by random (gives a random sample of all cards matching the given filters)

note: may not be used with `page[cursor]`
''', language_tag='en', mediatype='text/markdown; charset=utf-8')},
    },

    # attributes:
    TROVE.totalResultCount: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('totalResultCount', language_tag='en')},
    },
    TROVE.matchEvidence: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('matchEvidence', language_tag='en')},
    },
    TROVE.focusIdentifier: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        # TODO: rename to focusIdentifier in jsonapi
        JSONAPI_MEMBERNAME: {literal('resourceIdentifier', language_tag='en')},
    },
    TROVE.resourceMetadata: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('resourceMetadata', language_tag='en')},
    },
    TROVE.matchingHighlight: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('matchingHighlight', language_tag='en')},
    },
    TROVE.propertyPathKey: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('propertyPathKey', language_tag='en')},
    },
    TROVE.propertyPath: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('propertyPath', language_tag='en')},
    },
    TROVE.osfmapPropertyPath: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('osfmapPropertyPath', language_tag='en')},
    },
    TROVE.propertyPathSet: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('propertyPathSet', language_tag='en')},
    },
    TROVE.osfmapPropertyPathSet: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('osfmapPropertyPathSet', language_tag='en')},
    },
    TROVE.filterType: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty},
        JSONAPI_MEMBERNAME: {literal('filterType', language_tag='en')},
    },
    TROVE.filterValue: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('filterValueSet', language_tag='en')},
    },
    TROVE.cardsearchResultCount: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('cardSearchResultCount', language_tag='en')},
    },
    TROVE.suggestedFilterOperator: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('suggestedFilterOperator', language_tag='en')},
    },

    # relationships:
    TROVE.searchResultPage: {
        RDF.type: {RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {literal('searchResultPage', language_tag='en')},
    },
    TROVE.evidenceCard: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {literal('evidenceCard', language_tag='en')},
    },
    TROVE.relatedPropertyList: {
        RDF.type: {RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {literal('relatedProperties', language_tag='en')},
    },
    TROVE.indexCard: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {literal('indexCard', language_tag='en')},
    },

    # values:
    TROVE['ten-thousands-and-more']: {
        JSONAPI_MEMBERNAME: {literal('ten-thousands-and-more', language_tag='en')},
    },
    TROVE['any-of']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('any-of', language_tag='en')},
    },
    TROVE['none-of']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('none-of', language_tag='en')},
    },
    TROVE['is-absent']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('is-absent', language_tag='en')},
    },
    TROVE['is-present']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('is-present', language_tag='en')},
    },
    TROVE.before: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('before', language_tag='en')},
    },
    TROVE.after: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('after', language_tag='en')},
    },
    TROVE['at-date']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('at-date', language_tag='en')},
    },

    # other:
    RDF.type: {
        JSONAPI_MEMBERNAME: {literal('@type')},
    },
}

trove_labeler = IriLabeler(
    TROVE_API_VOCAB,
    label_iri=JSONAPI_MEMBERNAME,
    acceptable_prefixes=('trove:',),
)


def trove_indexcard_namespace():
    return IriNamespace(f'{settings.SHARE_WEB_URL}trove/index-card/')


def trove_indexcard_iri(indexcard_uuid):
    return trove_indexcard_namespace()[str(indexcard_uuid)]
