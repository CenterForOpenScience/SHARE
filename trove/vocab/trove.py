from django.conf import settings
from django.urls import reverse
from primitive_metadata.primitive_rdf import (
    IriNamespace,
    RdfTripleDictionary,
    literal,
    literal_json,
)

from trove.util.iri_labeler import IriLabeler
from trove.util.iris import get_sufficiently_unique_iri
from trove.vocab.jsonapi import (
    JSONAPI_MEMBERNAME,
    JSONAPI_ATTRIBUTE,
    JSONAPI_RELATIONSHIP,
)
from trove.vocab.osfmap import osfmap_labeler, DATE_PROPERTIES
from trove.vocab.namespaces import TROVE, RDF, RDFS, OWL, DCTERMS, SKOS


# some assumed-safe assumptions for iris in trovespace:
# - a name ending in forward slash (`/`) is a namespace
# - an iri fragment (after `#`) is a `,`-separated list
#   of iris; a path of predicates from the root of that
#   index card (for the iri with `#` and after removed)
# - TODO: each iri is an irL that resolves to rdf, html


def _literal_markdown(text: str, *, language: str):
    return literal(text, language=language, mediatype='text/markdown;charset=utf-8')


def _browse_link(iri: str):
    return reverse('trovetrove:browse-iri', kwargs={
        'iri': get_sufficiently_unique_iri(iri),
    })


TROVE_API_VOCAB: RdfTripleDictionary = {
    TROVE.search_api: {
        RDFS.label: {literal('trove search api', language='en')},
        RDFS.comment: {literal('trove (noun): a store of valuable or delightful things.', language='en')},
        TROVE.usesConcept: {
            TROVE.propertyPath,
        },
        TROVE.hasPath: {
            TROVE['path/card'],
            # TODO maybe: TROVE['path/value'],
            TROVE['path/card-search'],
            TROVE['path/value-search'],
            # TODO: TROVE['path/field-search'],
        },
        DCTERMS.description: {_literal_markdown('''
''', language='en')},
    },

    # types:
    TROVE.Indexcard: {
        RDF.type: {RDFS.Class, SKOS.Concept},
        RDFS.label: {literal('index-card', language='en')},
        JSONAPI_MEMBERNAME: {literal('index-card', language='en')},
        DCTERMS.description: {_literal_markdown('''an **index-card** is
a metadata record about a specific thing.

that thing is called the "focus" of the index-card and is identified by a "focus iri"
-- any thing may be identified by multiple iris, but choose one within an index-card
(and perhaps include the others with `owl:sameAs`)

the metadata about the thing is a quoted [rdf graph](https://www.w3.org/TR/rdf11-concepts/#data-model) in which every triple is reachable from the card's focus iri
following predicates as directed edges from subject to object.

there is not (yet) any size limit for an index-card's metadata,
but it is intended to be small enough for an old computer to use naively, all at once
(let's start the conversation at 4 KiB -- might be nice to fit in one page of memory)
''', language='en')},

    },
    TROVE.Cardsearch: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('index-card-search', language='en')},
    },
    TROVE.Valuesearch: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('index-value-search', language='en')},
    },
    TROVE.SearchResult: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('search-result', language='en')},
    },
    TROVE.RelatedPropertypath: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('related-property-path', language='en')},
    },
    TROVE.TextMatchEvidence: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('TextMatchEvidence', language='en')},
    },
    TROVE.IriMatchEvidence: {
        RDF.type: {RDFS.Class},
        JSONAPI_MEMBERNAME: {literal('IriMatchEvidence', language='en')},
    },

    # paths:
    TROVE['path/card-search']: {
        TROVE.iriPath: {literal('/trove/index-card-search')},
        TROVE.hasParameter: {
            TROVE.cardSearchText,
            TROVE.cardSearchFilter,
            TROVE.pageSize,
            TROVE.pageCursor,
            TROVE.sort,
            # TROVE.include,
        },
        RDFS.label: {literal('index-card-search', language='en')},
        RDFS.comment: {literal('search for index-cards based on the metadata they contain', language='en')},
        DCTERMS.description: {_literal_markdown('''**index-card-search** is
a way to find resources based on this metadata trove
''', language='en')},
    },
    TROVE['path/value-search']: {
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
        RDFS.label: {literal('index-value-search', language='en')},
        RDFS.comment: {literal('search for iri values based on how they are used', language='en')},
        DCTERMS.description: {_literal_markdown('''**index-value-search** is
a way to find iri values that could be used in a cardSearchFilter
''', language='en')},
    },
    TROVE['path/card']: {
        RDFS.label: {literal('index-card', language='en')},
        RDFS.comment: {literal('get a specific index-card by id', language='en')},
        TROVE.iriPath: {literal('/trove/index-card/{indexCardId}')},
        TROVE.hasParameter: {TROVE.indexCardId},
        TROVE.usesConcept: {TROVE.Indexcard},
    },

    # parameters:
    TROVE.cardSearchText: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE, TROVE.QueryParameter},
        JSONAPI_MEMBERNAME: {literal('cardSearchText', language='en')},
        RDFS.label: {literal('cardSearchText', language='en')},
        RDFS.comment: {literal('free-text search query', language='en')},
        TROVE.jsonSchema: {literal_json({'type': 'string'})},
        DCTERMS.description: {_literal_markdown('''**cardSearchText** is
a query parameter for free-text search, e.g. `cardSearchText=foo`

special characters in search text:

* `"` (double quotes): use on both sides of a word or phrase to require exact text match
  -- without quotes, text search is fuzzier and more approximate
* `-` (hyphen): use before a word or quoted phrase (before the leading `"`) to require
  that the exact word or phrase be absent
''', language='en')},
    },
    TROVE.cardSearchFilter: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE, TROVE.QueryParameter},
        JSONAPI_MEMBERNAME: {literal('cardSearchFilter', language='en')},
        RDFS.label: {literal('cardSearchFilter', language='en')},
        RDFS.comment: {literal('filter to index-cards with specific IRIs at specific locations', language='en')},
        TROVE.jsonSchema: {literal_json({'type': 'string'})},
        DCTERMS.description: {_literal_markdown('''**cardSearchFilter** is
a query parameter to narrow an index-card-search (or to narrow the card-search
context of an index-value-search) based on values at specific paths.

each cardSearchFilter has one or two bracketed parameters:
`cardSearchFilter[<propertypath_set>][<filter_operator>]=<value_iris>`

* `propertypath_set`: comma-separated **property-path** set
* `filter_operator`: (TODO: list operators)
* `value_iris`: comma-separated iri set
''', language='en')},
    },
    TROVE.valueSearchPropertyPath: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE, TROVE.QueryParameter, TROVE.RequiredParameter},
        JSONAPI_MEMBERNAME: {literal('valueSearchPropertyPath', language='en')},
        RDFS.label: {literal('valueSearchPropertyPath', language='en')},
        RDFS.comment: {literal('the location to look for values in index-cards', language='en')},
        TROVE.jsonSchema: {literal_json({'type': 'string'})},
        DCTERMS.description: {_literal_markdown('''**valueSearchPropertyPath** is
a required query parameter for index-value-search that indicates (with a
dot-separated path of short-hand IRIs) where in an index-card the resulting values must be used

* `valueSearchPropertyPath=creator`
* `valueSearchPropertyPath=creator.affiliation`

note: multiple property paths are not supported
''', language='en')},
    },
    TROVE.valueSearchText: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE, TROVE.QueryParameter},
        RDFS.label: {literal('valueSearchText', language='en')},
        JSONAPI_MEMBERNAME: {literal('valueSearchText', language='en')},
        RDFS.comment: {literal('free-text search (within a title, name, or label associated with an IRI)', language='en')},
        TROVE.jsonSchema: {literal_json({'type': 'string'})},
        DCTERMS.description: {_literal_markdown('''**valueSearchText** is
a query parameter that matches text closely associated with each value
(specifically `dcterms:title`, `foaf:name`, and `rdfs:label`)
''', language='en')},
    },
    TROVE.indexCardId: {
        RDF.type: {RDF.Property, TROVE.PathParameter},
        RDFS.label: {literal('indexCardId', language='en')},
        JSONAPI_MEMBERNAME: {literal('id', language='en')},
        RDFS.comment: {literal('unique identifier for an index-card', language='en')},
        TROVE.jsonSchema: {literal_json({'type': 'string'})},
        DCTERMS.description: {_literal_markdown('''
each index-card is uniquely identified by a UUID
''', language='en')},
    },
    TROVE.valueSearchFilter: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE, TROVE.QueryParameter},
        JSONAPI_MEMBERNAME: {literal('valueSearchFilter', language='en')},
        RDFS.label: {literal('valueSearchFilter', language='en')},
        RDFS.comment: {literal('filter to values that match a specific IRI or have a specific type', language='en')},
        TROVE.jsonSchema: {literal_json({'type': 'string'})},
        DCTERMS.description: {_literal_markdown('''**valueSearchFilter** is
a query parameter for narrowing an index-value-search

it may be used only two ways:

* `valueSearchFilter[sameAs]=<iri>` to request a specific value by IRI
* `valueSearchFilter[resourceType]=<type_iri>` to request values used with `rdf:type <type_iri>`
''', language='en')},
    },
    TROVE.pageCursor: {
        RDF.type: {TROVE.QueryParameter},
        RDFS.label: {literal('page[cursor]', language='en')},
        JSONAPI_MEMBERNAME: {literal('page[cursor]', language='en')},
        RDFS.comment: {literal('get an additional page from a prior search', language='en')},
        TROVE.jsonSchema: {literal_json({'type': 'string'})},
        DCTERMS.description: {_literal_markdown('''**page[cursor]** is
a query parameter for getting a specific page from an earlier search

links with `page[cursor]` are included in some api responses, but the
structure of a cursor is deliberately opaque and may change over time,
so cursor links may not be valid forever -- recommend starting a fresh
search each time

may not be used with `page[size]` or `sort`
''', language='en')},
    },
    TROVE.pageSize: {
        RDF.type: {TROVE.QueryParameter},
        RDFS.label: {literal('page[size]', language='en')},
        JSONAPI_MEMBERNAME: {literal('page[size]', language='en')},
        RDFS.comment: {literal('maximum number of search results returned at once', language='en')},
        TROVE.jsonSchema: {literal_json({'type': 'number'})},
        DCTERMS.description: {_literal_markdown('''**page[size]** is
a query parameter to control the maximum number of results returned at once

integer value, e.g. `page[size]=7` (default `13`)

may not be used with `page[cursor]`
''', language='en')},
    },

    TROVE.sort: {
        RDF.type: {TROVE.QueryParameter},
        RDFS.label: {literal('sort', language='en')},
        JSONAPI_MEMBERNAME: {literal('sort', language='en')},
        RDFS.comment: {literal('how to order search results', language='en')},
        TROVE.jsonSchema: {literal_json({'type': 'string'})},
        DCTERMS.description: {_literal_markdown(f'''**sort** is
a query param to control ordering of search results

accepts a short-hand iri for a date property:
{", ".join(f"`{osfmap_labeler.label_for_iri(_date_iri)}`" for _date_iri in DATE_PROPERTIES)}

prefix with `-` to sort descending (latest first), otherwise sorts ascending (earliest first)

if missing (or if `sort=-relevance`), results are sorted by some notion of
relevance to the request's search-text or (if no search-text) by random.

may not be used with `page[cursor]`
''', language='en')},
    },

    # attributes:
    TROVE.totalResultCount: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('totalResultCount', language='en')},
    },
    TROVE.matchEvidence: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('matchEvidence', language='en')},
    },
    TROVE.focusIdentifier: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        # TODO: rename to focusIdentifier in jsonapi
        JSONAPI_MEMBERNAME: {literal('resourceIdentifier', language='en')},
    },
    TROVE.resourceMetadata: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('resourceMetadata', language='en')},
    },
    TROVE.matchingHighlight: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('matchingHighlight', language='en')},
    },
    TROVE.propertyPathKey: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('propertyPathKey', language='en')},
    },
    TROVE.propertyPath: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        RDFS.label: {literal('property-path', language='en')},
        JSONAPI_MEMBERNAME: {literal('propertyPath', language='en')},
        DCTERMS.description: {_literal_markdown('''a **property-path** is
a dot-separated path of short-hand IRIs -- currently only OSFMAP shorthand
(TODO: link)

for example, `creator.name` is parsed as a two-step path that follows
`creator` (aka `dcterms:creator`, `<http://purl.org/dc/terms/creator>`) and then `name` (aka `foaf:name`, `<http://xmlns.com/foaf/0.1/name>`)

most places that allow one property-path also accept a comma-separated set of paths,
like `title,description` (which is parsed as two paths: `title` and `description`)
or `creator.name,affiliation.name,funder.name` (which is parsed as three paths: `creator.name`,
`affiliation.name`, and `funder.name`)

the special path segment `*` matches any property

* `*`: match text values one step away from the focus (default for `cardSearchText=` without `[]`)
* `*.*`: match text values exactly two steps away
* `*,*.*`: match text values one OR two steps away
* `*,creator.name`: match text values one step away OR at the specific path `creator.name`

(currently, if a path contains `*`, then every step must be `*`
-- mixed paths like `*.affiliation` are not supported)
''', language='en')},
    },
    TROVE.osfmapPropertyPath: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('osfmapPropertyPath', language='en')},
    },
    TROVE.propertyPathSet: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('propertyPathSet', language='en')},
    },
    TROVE.osfmapPropertyPathSet: {
        RDF.type: {RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('osfmapPropertyPathSet', language='en')},
    },
    TROVE.filterType: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty},
        JSONAPI_MEMBERNAME: {literal('filterType', language='en')},
    },
    TROVE.filterValue: {
        RDF.type: {RDF.Property},
        JSONAPI_MEMBERNAME: {literal('filterValueSet', language='en')},
    },
    TROVE.cardsearchResultCount: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('cardSearchResultCount', language='en')},
    },
    TROVE.suggestedFilterOperator: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {literal('suggestedFilterOperator', language='en')},
    },

    # relationships:
    TROVE.searchResultPage: {
        RDF.type: {RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {literal('searchResultPage', language='en')},
    },
    TROVE.evidenceCard: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {literal('evidenceCard', language='en')},
    },
    TROVE.relatedPropertyList: {
        RDF.type: {RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {literal('relatedProperties', language='en')},
    },
    TROVE.indexCard: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {literal('indexCard', language='en')},
    },

    # values:
    TROVE['ten-thousands-and-more']: {
        JSONAPI_MEMBERNAME: {literal('ten-thousands-and-more', language='en')},
    },
    TROVE['any-of']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('any-of', language='en')},
    },
    TROVE['none-of']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('none-of', language='en')},
    },
    TROVE['is-absent']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('is-absent', language='en')},
    },
    TROVE['is-present']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('is-present', language='en')},
    },
    TROVE.before: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('before', language='en')},
    },
    TROVE.after: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('after', language='en')},
    },
    TROVE['at-date']: {
        RDF.type: {TROVE.FilterOperator},
        JSONAPI_MEMBERNAME: {literal('at-date', language='en')},
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
