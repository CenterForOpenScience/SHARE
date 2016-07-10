Elasticsearch
=============

SHARE has an elasticsearch API endpoint that can be used for searching SHARE's normalized data, as well as for compiling
summary statistics and analyses of the completeness of data from the various sources.


Accessing the Search API
########################

You can acess the API via the command line with curl::

    curl -H "Content-Type: application/json" -X POST -d '{
        "query": {
            "query_string" : {
                "query" : "test"
            }
        }
    }' http://localhost:8000/api/search/abstractcreativework/_search

For more information on sending elasticsearch queries and aggregations, check out the `elasticsearch query DSL documentation  <https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html>`_.

Tutorials
*********

For a detailed series of tutorials on how to use the SHARE Search API, check out `this repository on GitHub  <https://github.com/erinspace/share_tutorials>`_.


sharepa - SHARE Parsing and Analysis Library
********************************************

You can also use ``sharepa`` - a python library for parsing SHARE data that connects directly to the search API. It is based on the
`elasticsearch DSL  <http://elasticsearch-dsl.readthedocs.io/en/latest/index.html>`_.

Install sharepa with::

    pip install sharepa

You can see the `source code for sharepa on GitHub  <https://github.com/CenterForOpenScience/sharepa>`_.

See some tutorials on how to use sharepa by visiting `this repository on GitHub  <https://github.com/erinspace/share_tutorials>`_.
