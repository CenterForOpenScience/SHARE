# How to use the API

## Harvesting metadata records in bulk

`/oaipmh` -- an implementation of the Open Access Initiative's [Protocol for Metadata Harvesting](https://www.openarchives.org/OAI/openarchivesprotocol.html), an open standard for harvesting metadata
from open repositories. You can use this to list metadata in bulk, or query by a few simple
parameters (date range or source).


## Searching metadata records

`/api/v2/search/creativeworks/_search` -- an elasticsearch API endpoint that can be used for
searching metadata records and for compiling summary statistics and analyses of the
completeness of data from the various sources.

You can search by sending a GET request with the query parameter `q`, or a POST request
with a body that conforms to the [elasticsearch query DSL](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html).

For example, the following two queries are equivalent:
```
GET https://share.osf.io/api/v2/search/creativeworks/_search?q=badges
```
```
POST https://share.osf.io/api/v2/search/creativeworks/_search
{
    "query": {
        "query_string" : {
            "query" : "badges"
        }
    }
}
```

You can also use the [SHARE Discover page](https://share.osf.io/discover) to generate query DSL.
Use the filters in the sidebar to construct a query, then click "View query body" to see the query in JSON form.


### Fields Indexed by Elasticsearch

The search endpoint has the following metadata fields available:

    'title'
    'description'
    'type'
    'date'
    'date_created'
    'date_modified
    'date_updated'
    'date_published'
    'tags'
    'subjects'
    'sources'
    'language'
    'contributors'
    'funders'
    'publishers'

#### Date fields
There are five date fields, and each has a different meaning. Two are given to SHARE by the data source:

``date_published``
    When the work was first published, issued, or made publicly available in any form.
    Not all sources provide this, so some works in SHARE have no ``date_published``.
``date_updated``
    When the work was last updated by the source. For example, an OAI-PMH record's ``<datestamp>``.
    Most works have a ``date_updated``, but some sources do not provide this.

Three date fields are populated by SHARE itself:

``date_created``
    When SHARE first ingested the work and added it to the SHARE dataset. Every work has a ``date_created``.
``date_modified``
    When SHARE last ingested the work and modified the work's record in the SHARE dataset. Every work
    has a ``date_modified``.
``date``
    Because many works may not have ``date_published`` or ``date_updated`` values, sorting and filtering works
    by date can be confusing. The ``date`` field is intended to help. It contains the most useful available
    date. If the work has a ``date_published``, ``date`` contains the value of ``date_published``. If the work
    has no ``date_published`` but does have ``date_updated``, ``date`` is set to ``date_updated``. If the work
    has neither ``date_published`` nor ``date_updated``, ``date`` is set to ``date_created``.

## Pushing metadata records
> NOTE: currently used only by other COS projects, not yet for public use

`/api/v2/normalizeddata` -- how to push data into SHARE/Trove (instead of waiting to be harvested)

```
POST /api/v2/normalizeddata HTTP/1.1
Host: share.osf.io
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/vnd.api+json

{
    "data": {
        "type": "NormalizedData",
        "attributes": {
            "data": {
                "central_node_id": '...',
                "@graph": [/* see below */]
            }
        }
    }
}
```

### NormalizedData format
The normalized metadata format used internally by SHARE/Trove is a subset of
[JSON-LD graph](https://www.w3.org/TR/json-ld/#named-graphs).
Each graph node must contain `@id` and `@type`, plus other key/value pairs
according to the
["SHARE schema"](https://github.com/CenterForOpenScience/SHARE/blob/develop/share/schema/schema-spec.yaml)

In this case, `@id` will always be a "blank" identifier, which begins with `'_:'`
and is used only to define relationships between nodes in the graph -- nodes
may reference each other with `@id`/`@type` pairs --
e.g. `{'@id': '...', '@type': '...'}`

Example serialization: The following SHARE-style JSON-LD document represents a
preprint with one "creator" and one identifier -- the graph contains nodes for
the preprint, person, and identifier, plus another node representing the
"creator" relationship between the preprint and person:
```
{
    'central_node_id': '_:foo',
    '@graph': [
        {
            '@id': '_:foo',
            '@type': 'preprint',
            'title': 'This is a preprint!',
        },
        {
            '@id': '_:bar',
            '@type': 'workidentifier',
            'uri': 'https://osf.io/foobar/',
            'creative_work': {'@id': '_:foo', '@type': 'preprint'}
        },
        {
            '@id': '_:baz',
            '@type': 'person',
            'name': 'Magpie Jones'
        },
        {
            '@id': '_:qux',
            '@type': 'creator',
            'creative_work': {'@id': '_:foo', '@type': 'preprint'},
            'agent': {'@id': '_:baz', '@type': 'person'}
        }
    ]
}
```
