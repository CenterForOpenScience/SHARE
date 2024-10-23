import functools
import urllib.parse

from django.conf import settings
from django.urls import reverse
from primitive_metadata.primitive_rdf import (
    IriNamespace,
    IriShorthand,
    RdfTripleDictionary,
    literal,
    literal_json,
    blanknode,
)

from trove.util.shorthand import build_shorthand_from_thesaurus
from trove.vocab.jsonapi import (
    JSONAPI_MEMBERNAME,
    JSONAPI_ATTRIBUTE,
    JSONAPI_RELATIONSHIP,
)
from trove.vocab.osfmap import (
    DATE_PROPERTIES,
    OSFMAP_LINK,
    osfmap_shorthand,
)
from trove.vocab.namespaces import (
    DCTERMS,
    OWL,
    RDF,
    RDFS,
    SKOS,
    TROVE,
    NAMESPACES_SHORTHAND,
)


# some assumed-safe assumptions for iris in trovespace:
# - a name ending in forward slash (`/`) is a namespace
# - an iri fragment (after `#`) is a `,`-separated list
#   of iris; a path of predicates from the root of that
#   index card (for the iri with `#` and after removed)
# - TODO: each iri is an irL that resolves to rdf, html


def _literal_markdown(text: str, *, language: str):
    return literal(text, language=language, mediatype='text/markdown;charset=utf-8')


def trove_browse_link(iri: str):
    return urllib.parse.urljoin(
        reverse('trovetrove:browse-iri'),
        f'?iri={urllib.parse.quote(iri)}',
    )


TROVE_API_THESAURUS: RdfTripleDictionary = {
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
        DCTERMS.description: {_literal_markdown('''the **trove search api** helps
navigate a trove of metadata.

currently, that trove of metadata is mostly focused on [osf.io](https://osf.io)
and the trove api is focused on supporting [osf:search](https://osf.io/search),
but both are open for anyone to use.
''', language='en')},
    },

    # types:
    TROVE.Indexcard: {
        RDF.type: {RDFS.Class, SKOS.Concept},
        RDFS.label: {literal('index-card', language='en')},
        JSONAPI_MEMBERNAME: {literal('index-card', language='en')},
        DCTERMS.description: {_literal_markdown(f'''an **index-card** is
a metadata record about a specific thing.

that thing is called the "focus" of the index-card and is identified by a "focus iri"
-- any thing may be identified by multiple iris, but choose one within an index-card
(and perhaps include the others with `owl:sameAs`)

the metadata about the thing is a quoted [rdf graph](https://www.w3.org/TR/rdf11-concepts/#data-model)
in which every triple is reachable from the card's focus iri
following predicates as directed edges from subject to object.

there is not (yet) any size limit for an index-card's metadata,
but it is intended to be small enough for an old computer to use naively, all at once
(let's start the conversation at 4 KiB -- might be nice to fit in one page of memory)

### jsonapi representation
the index-card's `resourceMetadata` property contains a quoted graph, independent
of the rest of the response.

when represented as `application/vnd.api+json` (jsonapi), the `resourceMetadata` attribute
contains a json object that has:

* `@id` with the focus iri
* `@type` with the focus resource's `rdf:type`
* property keys from [OSFMAP]({OSFMAP_LINK}) shorthand (each corresponding to an iri)
* property values as lists of objects:
  * literal text as `{{"@value": "..."}}`
  * iri references as `{{"@id": "..."}}`
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
            TROVE.acceptMediatype,
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
        TROVE.example: {
            blanknode({
                RDFS.label: {literal('card-search-with-text', language='en')},
                RDFS.comment: {literal('card-search with text', language='en')},
                DCTERMS.description: {_literal_markdown('''
search index-cards that match a fuzzy text search for the word "word" in the title (aka `dcterms:title`, `<http://purl.org/dc/terms/title>`)

uses query parameter:
```
cardSearchText[title]=word
```
''', language='en')},
                RDF.value: {literal('/trove/index-card-search?cardSearchText[title]=word&acceptMediatype=application/vnd.api%2Bjson')},
            }),
            blanknode({
                RDFS.label: {literal('card-search-with-filter', language='en')},
                RDFS.comment: {literal('card-search with filter', language='en')},
                DCTERMS.description: {_literal_markdown('''
search index-cards that have at least one creator affiliated with [COS](https://cos.io)

uses query parameter:
```
cardSearchFilter[creator.affiliation]=https://cos.io
```
''', language='en')},
                RDF.value: {literal('/trove/index-card-search?cardSearchFilter[creator.affiliation]=https://cos.io&acceptMediatype=application/vnd.api%2Bjson')},
            }),
            blanknode({
                RDFS.label: {literal('card-search-with-date-filter', language='en')},
                RDFS.comment: {literal('card-search with date filter', language='en')},
                DCTERMS.description: {_literal_markdown('''
searches index-cards with `dateCreated` (aka `dcterms:created`, `<http://purl.org/dc/terms/created>`)
values after 2022

uses query parameter:
```
cardSearchFilter[dateCreated][after]=2022
```
''', language='en')},
                RDF.value: {literal('/trove/index-card-search?cardSearchFilter[dateCreated][after]=2022&acceptMediatype=application/vnd.api%2Bjson')},
            }),
            blanknode({
                RDFS.label: {literal('card-search-with-star-path', language='en')},
                RDFS.comment: {literal('card-search with star path', language='en')},
                DCTERMS.description: {_literal_markdown('''
searches index-cards with a specific iri value at any property

uses query parameter:
```
cardSearchFilter[*]=https://osf.io
```
''', language='en')},
                RDF.value: {literal('/trove/index-card-search?cardSearchFilter[*]=https://osf.io&acceptMediatype=application/vnd.api%2Bjson')},
            }),
            blanknode({
                RDFS.label: {literal('card-search-with-multiple-filter', language='en')},
                RDFS.comment: {literal('card-search with multiple filters', language='en')},
                DCTERMS.description: {_literal_markdown('''
searches for index-cards that have a `funder` and do not have an `affiliation`

uses query parameters:
```
cardSearchFilter[funder][is-present]
cardSearchFilter[affiliation][is-absent]
```
''', language='en')},
                RDF.value: {literal('/trove/index-card-search?cardSearchFilter[funder][is-present]&cardSearchFilter[affiliation][is-absent]&acceptMediatype=application/vnd.api%2Bjson')},
            }),
        },
    },
    TROVE['path/value-search']: {
        TROVE.iriPath: {literal('/trove/index-value-search')},
        TROVE.hasParameter: {
            TROVE.acceptMediatype,
            TROVE.valueSearchPropertyPath,
            TROVE.cardSearchText,
            TROVE.cardSearchFilter,
            TROVE.valueSearchText,
            TROVE.valueSearchFilter,
            TROVE.pageSize,
            TROVE.pageCursor,
            # TROVE.sort,
            # TROVE.include,
        },
        RDFS.label: {literal('index-value-search', language='en')},
        RDFS.comment: {literal('search for iri values based on how they are used', language='en')},
        DCTERMS.description: {_literal_markdown('''**index-value-search** is
a way to find iri values that could be used in a cardSearchFilter
''', language='en')},
        TROVE.example: {
            blanknode({
                RDFS.label: {literal('value-search without card-search', language='en')},
                RDFS.comment: {literal('value-search without card-search', language='en')},
                DCTERMS.description: {_literal_markdown('''
search for iri values for the property `creator` (aka `dcterms:creator`,
`<http://purl.org/dc/terms/creator>`)

uses query parameter:
```
valueSearchPropertyPath=creator
```
''', language='en')},
                RDF.value: {literal('/trove/index-value-search?valueSearchPropertyPath=creator&acceptMediatype=application/vnd.api%2Bjson')},
            }),
            blanknode({
                RDFS.label: {literal('value-search with card-search', language='en')},
                RDFS.comment: {literal('value-search with card-search', language='en')},
                DCTERMS.description: {_literal_markdown('''
search for iri values for the property `creator` within the context of a card-search

uses query parameter:
```
valueSearchPropertyPath=creator
cardSearchText=sciency
cardSearchFilter[subject][is-present]
```
''', language='en')},
                RDF.value: {literal('/trove/index-value-search?valueSearchPropertyPath=creator&cardSearchText=sciency&cardSearchFilter[subject][is-present]&acceptMediatype=application/vnd.api%2Bjson')},
            }),
            blanknode({
                RDFS.label: {literal('value-search specific iri', language='en')},
                RDFS.comment: {literal('value-search specific iri', language='en')},
                DCTERMS.description: {_literal_markdown('''
search for a specific iri value in the property `creator`

uses query parameter:
```
valueSearchPropertyPath=creator
valueSearchFilter[sameAs]=https://orcid.org/0000-0002-6155-6104
```
''', language='en')},
                RDF.value: {literal('/trove/index-value-search?valueSearchPropertyPath=creator&valueSearchFilter[sameAs]=https://orcid.org/0000-0002-6155-6104&acceptMediatype=application/vnd.api%2Bjson')},
            }),
            blanknode({
                RDFS.label: {literal('value-search by value type', language='en')},
                RDFS.comment: {literal('value-search by value type', language='en')},
                DCTERMS.description: {_literal_markdown('''
search for iri values that are used as `creator` and have `rdf:type` `Person` (aka `foaf:Person`)

uses query parameter:
```
valueSearchPropertyPath=creator
valueSearchFilter[resourceType]=Person
```
''', language='en')},
                RDF.value: {literal('/trove/index-value-search?valueSearchPropertyPath=creator&acceptMediatype=application/vnd.api%2Bjson')},
            }),
            blanknode({
                RDFS.label: {literal('value-search with text', language='en')},
                RDFS.comment: {literal('value-search with text', language='en')},
                DCTERMS.description: {_literal_markdown('''
search for iri values used as `license` that have "cc" in their label
(`rdfs:label`, `dcterms:title`, or `foaf:name`)

uses query parameter:
```
valueSearchPropertyPath=license
valueSearchText=cc
```
''', language='en')},
                RDF.value: {literal('/trove/index-value-search?valueSearchPropertyPath=license&valueSearchText=cc&acceptMediatype=application/vnd.api%2Bjson')},
            }),
        },
    },
    TROVE['path/card']: {
        RDFS.label: {literal('index-card', language='en')},
        RDFS.comment: {literal('get a specific index-card by id', language='en')},
        TROVE.iriPath: {literal('/trove/index-card/{indexCardId}')},
        TROVE.hasParameter: {
            TROVE.acceptMediatype,
            TROVE.indexCardId,
        },
        TROVE.usesConcept: {TROVE.Indexcard},
        TROVE.example: {
            blanknode({
                RDFS.label: {literal('get index-card', language='en')},
                RDFS.comment: {literal('get index-card', language='en')},
                DCTERMS.description: {_literal_markdown('''
get a specific index-card by id
''', language='en')},
                RDF.value: {literal_json({
                    "data": {
                        "id": "2cf01bc0-811e-4804-bcc7-b39364907464",
                        "type": "index-card",
                        "attributes": {
                            "resourceIdentifier": [
                                "http://foo.example/bv7mp"
                            ],
                            "resourceMetadata": {
                                "@id": "http://foo.example/bv7mp",
                                "resourceType": [
                                    {"@id": "Preprint"}
                                ],
                                "dateCreated": [
                                    {"@value": "2023-04-21"}
                                ],
                                "creator": [
                                    {
                                        "@id": "http://foo.example/vraye",
                                        "resourceType": [
                                            {"@id": "Person"},
                                            {"@id": "Agent"}
                                        ],
                                        "identifier": [
                                            {"@value": "http://foo.example/vraye"}
                                        ],
                                        "name": [
                                            {"@value": "Some Person"}
                                        ]
                                    }
                                ],
                                "dateCopyrighted": [
                                    {"@value": "2023"}
                                ],
                                "description": [
                                    {"@value": "words words words"}
                                ],
                                "identifier": [
                                    {"@value": "http://foo.example/bv7mp"}
                                ],
                                "dateModified": [
                                    {"@value": "2023-04-25"}
                                ],
                                "publisher": [
                                    {
                                        "@id": "http://foo.example/publisher",
                                        "resourceType": [
                                            {"@id": "Agent"},
                                            {"@id": "Organization"}
                                        ],
                                        "identifier": [
                                            {"@value": "http://foo.example/publisher"}
                                        ],
                                        "name": [
                                            {"@value": "Foo Publisher"}
                                        ]
                                    }
                                ],
                                "rights": [
                                    {
                                        "name": [
                                            {"@value": "No license"}
                                        ]
                                    }
                                ],
                                "rightsHolder": [
                                    {"@value": "nthnth"}
                                ],
                                "subject": [
                                    {
                                        "@id": "http://foo.example//",
                                        "resourceType": [
                                            {"@id": "Concept"}
                                        ],
                                        "inScheme": [
                                            {
                                                "@id": "https://bepress.com/reference_guide_dc/disciplines/",
                                                "resourceType": [
                                                    {"@id": "http://www.w3.org/2004/02/skos/core#ConceptScheme"}
                                                ],
                                                "title": [
                                                    {"@value": "bepress Digital Commons Three-Tiered Taxonomy"}
                                                ]
                                            }
                                        ],
                                        "prefLabel": [
                                            {"@value": "Medicine and Health Sciences"}
                                        ]
                                    },
                                    {
                                        "@id": "http://foo.example/v2/subjects/630cab2ccf30b1000187b723/",
                                        "resourceType": [
                                            {"@id": "Concept"}
                                        ],
                                        "inScheme": [
                                            {
                                                "@id": "https://bepress.com/reference_guide_dc/disciplines/",
                                                "resourceType": [
                                                    {"@id": "http://www.w3.org/2004/02/skos/core#ConceptScheme"}
                                                ],
                                                "title": [
                                                    {"@value": "bepress Digital Commons Three-Tiered Taxonomy"}
                                                ]
                                            }
                                        ],
                                        "prefLabel": [
                                            {"@value": "Law"}
                                        ]
                                    }
                                ],
                                "title": [
                                    {"@value": "aoaoao"}
                                ],
                                "resourceNature": [
                                    {
                                        "@id": "https://schema.datacite.org/meta/kernel-4.4/#Preprint",
                                        "displayLabel": [
                                            {
                                                "@value": "Preprint",
                                                "@language": "en"
                                            }
                                        ]
                                    }
                                ],
                                "accessService": [
                                    {"@id": "http://foo.example"}
                                ],
                                "hasPreregisteredAnalysisPlan": [
                                    {"@id": "http://foo.example/blah"}
                                ],
                                "hasPreregisteredStudyDesign": [
                                    {"@id": "http://foo.example/blah"}
                                ],
                                "keyword": [
                                    {"@value": "wibbleplop"},
                                    {"@value": "go"}
                                ],
                                "links": {
                                    "self": "http://localhost:8003/trove/index-card/2cf01bc0-811e-4804-bcc7-b39364907464"
                                }
                            }
                        }
                    }
                })},
            }),
        },
    },

    # parameters:
    TROVE.acceptMediatype: {
        RDF.type: {RDF.Property, TROVE.QueryParameter},
        JSONAPI_MEMBERNAME: {literal('acceptMediatype', language='en')},
        RDFS.label: {literal('acceptMediatype', language='en')},
        RDFS.comment: {literal('request a specific mediatype', language='en')},
        TROVE.jsonSchema: {literal_json({'type': 'string'})},
        DCTERMS.description: {_literal_markdown('''**acceptMediatype** is
a query parameter to request a specific [mediatype](https://www.iana.org/assignments/media-types/).

each api response is modeled as an [rdf graph](https://www.w3.org/TR/rdf11-concepts/#data-model),
which could be rendered into many different mediatypes.

stable mediatypes:

* `application/vnd.api+json`: [jsonapi](https://jsonapi.org/)
  to support [osf:search](https://osf.io/search)

unstable mediatypes (may change or sometimes respond 500):

* `text/html;charset=utf-8`: rdf as browsable html
* `text/turtle`: rdf as [turtle](https://www.w3.org/TR/turtle/)
* `application/ld+json`: rdf as [json-ld](https://www.w3.org/TR/json-ld11/)

`acceptMediatype` will override the `Accept` header, if present.
''', language='en')},
    },
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

accepts comma-separated property-paths in an optional bracketed parameter (default
`*]`, matches any one property), e.g. `cardSearchText[title,description]=foo`
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
* `filter_operator`: any one of the operators defined below
* `value_iris`: comma-separated iri set

### filter operators

operators on iri values:

* `any-of` (default): at least one of the value iris
* `none-of`: none of the value iris
* `is-present`: the property-path must exist, but its value does not matter
* `is-absent`: the property-path must not exist

operators on date values (may give date in `YYYY-MM-DD`, `YYYY-MM`, or `YYYY` format)

* `before`: before the given date (excluding the date itself)
* `after`: after the given date (excluding the date itself)
* `at-date`: within the given date

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

note: does not accept any bracketed parameters
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
{", ".join(f"`{osfmap_shorthand().compact_iri(_date_iri)}`" for _date_iri in DATE_PROPERTIES)}

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
        DCTERMS.description: {_literal_markdown(f'''a **property-path** is
a dot-separated path of short-hand IRIs, used in several api parameters

currently the only supported shorthand is defined by [OSFMAP]({OSFMAP_LINK})

for example, `creator.name` is parsed as a two-step path that follows
`creator` (aka `dcterms:creator`, `<http://purl.org/dc/terms/creator>`) and then `name` (aka `foaf:name`, `<http://xmlns.com/foaf/0.1/name>`)

most places that allow one property-path also accept a comma-separated set of paths,
like `title,description` (which is parsed as two paths: `title` and `description`)
or `creator.name,affiliation.name,funder.name` (which is parsed as three paths: `creator.name`,
`affiliation.name`, and `funder.name`)

the special path segment `*` matches any property

* `*`: match text values one step away from the focus
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
    TROVE.evidenceCardIdentifier: {
        RDF.type: {RDF.Property, OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {literal('evidenceCardIdentifier', language='en')},
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


@functools.cache
def trove_shorthand() -> IriShorthand:
    '''build iri shorthand that includes unprefixed terms (as defined in TROVE_API_THESAURUS)
    '''
    return build_shorthand_from_thesaurus(
        thesaurus=TROVE_API_THESAURUS,
        label_predicate=JSONAPI_MEMBERNAME,
        base_shorthand=NAMESPACES_SHORTHAND,
    )


@functools.cache
def trove_indexcard_namespace():
    return IriNamespace(f'{settings.SHARE_WEB_URL}trove/index-card/')


def trove_indexcard_iri(indexcard_uuid):
    return trove_indexcard_namespace()[str(indexcard_uuid)]
