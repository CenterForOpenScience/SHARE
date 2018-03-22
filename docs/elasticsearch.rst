Elasticsearch
=============

SHARE has an elasticsearch API endpoint that can be used for searching SHARE's normalized data, as well as for compiling
summary statistics and analyses of the completeness of data from the various sources.

https://share.osf.io/api/v2/search/creativeworks/_search

Fields Indexed by Elasticsearch
###############################

Elasticsearch can be used to search the following fields in the normalized data::

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

Date Fields
***********
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

Accessing the Search API
########################

Using curl
**********

You can acess the API via the command line using a basic query string with curl::

    curl -H "Content-Type: application/json" -X POST -d '{
        "query": {
            "query_string" : {
                "query" : "test"
            }
        }
    }' https://share.osf.io/api/v2/search/creativeworks/_search

The elasticsearch API also allows you to aggregate over the whole dataset. This query will also return an aggregation of which sources
do not have a value specified for the field "language"::


    curl -H "Content-Type: application/json" -X POST -d '{
        "aggs": {
            "sources": {
                "significant_terms": {
                    "percentage": {},
                    "size": 0,
                    "min_doc_count": 1,
                    "field": "sources"
                }
            }
        },
        "query": {
            "bool": {
                "must_not": [
                    {
                        "exists": {
                            "field": "language"
                        }
                    }
                ]
            }
        }
    }' https://share.osf.io/api/v2/search/creativeworks/_search

For more information on sending elasticsearch queries and aggregations, check out the `elasticsearch query DSL documentation  <https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html>`_.

You can also use the `SHARE Discover page <https://share.osf.io/discover>`_ to generate query DSL. Use the filters in the sidebar to construct a query, then click "View query body" to see the query in JSON form.


Searching for ORCIDs
*********************

Get all works where contributors have ORCID identifiers:
https://share.osf.io/api/v2/search/creativeworks/_search?q=lists.contributors.identifiers:orcid.org

In the results, the ORCID will be listed under:
_source → lists → contributors → (contributor) → identifiers ::

    {
        timed_out: false,
        hits: {
            total: 204235,
            hits: [
            {
                _id: "XXXX-XXX-XXX",
                _source: {
                    id: "XXXX-XXX-XXX",
                    date_updated: "2016-04-23T07:31:31+00:00",
                    title: "Title Example",
                    date: "2016-04-23T07:31:31+00:00",
                    description: "Example of a search result containing an ORCID.",
                    contributors: [...],
                    date_created: "2016-11-28T22:21:09.917395+00:00",
                    date_modified: "2016-11-29T14:18:49.745627+00:00",
                    date_published: null,
                    lists: {
                        contributors: [
                            {
                                given_name: "T.",
                                types: [
                                    "person",
                                    "agent"
                                ],
                                order_cited: 133,
                                identifiers: [
                                    "http://orcid.org/XXXX-XXXX-XXXX-XXXX"
                                ],
                                cited_as: "T. User",
                                family_name: "User",
                                relation: "creator",
                                name: "T. User",
                                type: "person",
                                id: "XXXX-XXX-XXX"
                            },
                        ...



Search for an ORCID identifier:
https://share.osf.io/api/v2/search/creativeworks/_search?q=lists.contributors.identifiers:”XXXX-XXXX-XXXX-XXXX”
