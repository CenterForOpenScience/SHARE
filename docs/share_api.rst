SHARE API
=========

The SHARE API generally complies with the `JSON-API`_ v1.0 spec, as should anyone using the SHARE API.

Check out the `browsable SHARE API docs`_!


Getting Started
---------------

Before pushing data to production it is highly recommended to use our staging environment.

1. Go to `the staging OSF`_ and `register for an account`_
2. Navigate to `staging SHARE`_ and login.
3. `Register to become a source`_.
4. Send an email to share-support@osf.io and wait for us to approve your account.
5. Once approved, the API token from your `staging SHARE profile page`_ can be used to push data.

To become a Source for production repeat the above steps at https://share.osf.io with a `production OSF account`_.

    .. note:: Our Staging enviroment is constantly being updated with new code. If something doesn't work, try again in a day or two before contacting us at share-support@osf.io

.. _the staging OSF: https://staging.osf.io
.. _register for an account: https://staging.osf.io/register/
.. _staging SHARE: https://staging-share.osf.io
.. _Register to become a source: https://staging-share.osf.io/registration
.. _staging SHARE profile page: https://staging-share.osf.io/profile
.. _production OSF account: https://staging.osf.io/register/


Paging in the API
-----------------

The SHARE API implements diffent paging strategies depending on the endpoint. All of them, however, conform to the `JSON-API paging spec`_.

  .. code-block:: python

    import requests

    r = requests.get(
        'https://share.osf.io/api/v2/normalizeddata/',
        headers={'Content-Type': 'application/vnd.api+json'}
    )
    next_link = r.json()['links']['next']


Push data directly into the SHARE database
------------------------------------------

Changes to the SHARE dataset, additions, modifications, or deletions (Not yet supported), are submitted as a subset of `JSON-LD graphs`_.
A change is represented as a JSON object with a single key, ``@graph``, containing a list of `JSON-LD nodes`_.

    .. code-block:: javascript

        {
            "@graph": [
                {
                    // Omitted...
                },
                {
                    // Omitted...
                },
                {
                    // Omitted...
                }
            ]
        }

- Each node MUST contain an ``@id`` and ``@type`` key.
- ``@id`` MUST be either a `blank node identifier`_ or the id of an existing object in the SHARE dataset.

    .. code-block:: javascript

        // GOOD: A blank identifier
        {
            "@id": "_:1234"
            // Omitted...
        }

        // GOOD: An existing object's ID
        {
            "@id": "46227-0C4-522"
            // Omitted...
        }

        // BAD: Anything that is not a string
        {
            "@id": 12
            // Omitted...
        }

        // BAD: A meaningless string
        {
            "@id": "FooBar"
            // Omitted...
        }

- ``@type`` MUST be a `SHARE type`_.

    .. note:: ``@type`` is case sensitive and expects title case, lowercase, or uppercase types.

    .. code-block:: javascript

        // GOOD: Title case for a type from the linked page
        {
            "@type": "Preprint"
            // Omitted...
        }

        // GOOD: All lowercase for a type from the linked page
        {
            "@type": "article"
            // Omitted...
        }

        // GOOD: All uppercase for a type from the linked page
        {
            "@type": "CREATIVEWORK"
            // Omitted...
        }

        // BAD: Other casing of a type from the linked page
        {
            "@type": "cReAtIvEwOrK"
            // Omitted...
        }

        // BAD: Anything else
        {
            "@type": "Unicorn"
            // Omitted...
        }

- Each node MUST match the `JSON schema`_ for its specified type (``@type``).

    .. note:: The JSON schemas for every type can be found `here <https://share.osf.io/api/v2/schema>`_.

    .. code-block:: javascript

        // GOOD: Following the schema
        {
            "@id": "_:abc",
            "@type": "Person",
            "given_name": "Tim"
            "family_name": "Errington"
        }

        // GOOD: Following the schema a different way
        {
            "@id": "_:abc",
            "@type": "Person",
            "name": "Tim Errington"
        }

        // BAD: Invalid data
        {
            "@id": "_:abc",
            "@type": "Article",
            "color": "Nine"
        }

- Nodes may reference either existing objects or nodes in the same graph.

    .. note:: The order of nodes in ``@graph`` does not matter.

    .. code-block:: javascript
       :emphasize-lines: 7, 21, 31, 41

        // GOOD: Referring to another node
        {
            "@graph": [{
                "@id": "_:123",
                "@type": "agentidentifier",
                "uri": "http://osf.io/juwia",
                "agent": {"@id": "_:abc", "@type": "person"}  // Refers the the node below
            }, {
                "@id": "_:abc",
                "@type": "person",
                "name": "Chris Seto",
            }]
        }

        // GOOD: Referring to an existing object
        {
            "@graph": [{
                "@id": "_:123",
                "@type": "agentidentifier",
                "uri": "http://osf.io/juwia",
                "agent": {"@id": "6403D-314-B83", "@type": "person"}
            }]
        }

        // BAD: Referring to a node that is not defined
        {
            "@graph": [{
                "@id": "_:123",
                "@type": "agentidentifier",
                "uri": "http://osf.io/juwia",
                "agent": {"@id": "_:abcd", "@type": "person"}  // _:abcd does not appear anywhere
            }]
        }

        // BAD: Referring to a node any way besides {"@id": "...", "@type": "..."}
        {
            "@graph": [{
                "@id": "_:123",
                "@type": "agentidentifier",
                "uri": "http://osf.io/juwia",
                "agent": "6403D-314-B83",  // Please don't
            }]
        }

- Finally, changes must be submitted in `JSON-API`_ format using `OAuth2`_ to authenticate

    .. note:: Yes, there are two ``data`` keys. Sorry.

    .. code-block:: http

        POST /api/v2/normalizeddata HTTP/1.1
        Host: share.osf.io
        Authorization: Bearer ACCESS_TOKEN
        Content-Type: application/vnd.api+json

        {
            "data": {
                "type": "NormalizedData",
                "attributes": {
                    "data": {
                        "@graph": [/* ... */]
                    }
                }
            }
        }

Example Data
~~~~~~~~~~~~

    .. code-block:: javascript

        {
            "@graph": [{
                "uri": "http://dx.doi.org/10.1038/EJCN.2016.211",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@type": "WorkIdentifier",
                "@id": "_:014eb1c53ba64c9c88bc46ef89cb2080"
            }, {
                "uri": "oai://nature.com/10.1038/ejcn.2016.211",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@type": "WorkIdentifier",
                "@id": "_:d058a287d60f45a48e7d0a9ecfd98bad"
            }, {
                "name": "M Santiago-Torres",
                "@type": "person",
                "@id": "_:760b02f6297a4bbd8fd6f2a0af306dd7"
            }, {
                "order_cited": 0,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:a632e7a0a5814e7fb1fdef1bec6895ab",
                "agent": {
                    "@type": "person",
                    "@id": "_:760b02f6297a4bbd8fd6f2a0af306dd7"
                },
                "cited_as": "M Santiago-Torres"
            }, {
                "name": "J De Dieu Tapsoba",
                "@type": "person",
                "@id": "_:15838a790c5d41508e5ad8f1327fbaa9"
            }, {
                "order_cited": 1,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:55cd617b118c43f5becb7647f17eba12",
                "agent": {
                    "@type": "person",
                    "@id": "_:15838a790c5d41508e5ad8f1327fbaa9"
                },
                "cited_as": "J De Dieu Tapsoba"
            }, {
                "name": "M Kratz",
                "@type": "person",
                "@id": "_:50098933694d4795a2653546cdc85493"
            }, {
                "order_cited": 2,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:3c75c1082fde4676a53d16111c7354d9",
                "agent": {
                    "@type": "person",
                    "@id": "_:50098933694d4795a2653546cdc85493"
                },
                "cited_as": "M Kratz"
            }, {
                "name": "J W Lampe",
                "@type": "person",
                "@id": "_:97eb79ce0005436894b52d53536d3ddc"
            }, {
                "order_cited": 3,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:671d6abea53442e1b50a2976cbe10ac7",
                "agent": {
                    "@type": "person",
                    "@id": "_:97eb79ce0005436894b52d53536d3ddc"
                },
                "cited_as": "J W Lampe"
            }, {
                "name": "K L Breymeyer",
                "@type": "person",
                "@id": "_:38b4cc174ea44f649257f86cf93effbc"
            }, {
                "order_cited": 4,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:b7676b36d1b4483e8008eedfbd1fb043",
                "agent": {
                    "@type": "person",
                    "@id": "_:38b4cc174ea44f649257f86cf93effbc"
                },
                "cited_as": "K L Breymeyer"
            }, {
                "name": "L Levy",
                "@type": "person",
                "@id": "_:b809383685844464ab2a4203c8b5ee98"
            }, {
                "order_cited": 5,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:fecd2c815ba84e1d9455b1d31182b267",
                "agent": {
                    "@type": "person",
                    "@id": "_:b809383685844464ab2a4203c8b5ee98"
                },
                "cited_as": "L Levy"
            }, {
                "name": "X Song",
                "@type": "person",
                "@id": "_:007fca2333e74ed38e3f1b92a13662ae"
            }, {
                "order_cited": 6,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:b0c9846c388541c39f0cc42056dc1de2",
                "agent": {
                    "@type": "person",
                    "@id": "_:007fca2333e74ed38e3f1b92a13662ae"
                },
                "cited_as": "X Song"
            }, {
                "name": "A Villase\u00f1or",
                "@type": "person",
                "@id": "_:78a4cd8407a74e0a81468ba3cd2658ed"
            }, {
                "order_cited": 7,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:96f9851b68444d9fa5ad7faab1f1d518",
                "agent": {
                    "@type": "person",
                    "@id": "_:78a4cd8407a74e0a81468ba3cd2658ed"
                },
                "cited_as": "A Villase\u00f1or"
            }, {
                "name": "C-Y Wang",
                "@type": "person",
                "@id": "_:6ffa6c228c75476c9cc089053be6b3f1"
            }, {
                "order_cited": 8,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:f39c7fa402ca4028a78798dc67eb5dff",
                "agent": {
                    "@type": "person",
                    "@id": "_:6ffa6c228c75476c9cc089053be6b3f1"
                },
                "cited_as": "C-Y Wang"
            }, {
                "name": "L Fejerman",
                "@type": "person",
                "@id": "_:3a15f900ccba4d5cbeade9c48f857f60"
            }, {
                "order_cited": 9,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:51fbd9a4043b41f29407522e3ef50534",
                "agent": {
                    "@type": "person",
                    "@id": "_:3a15f900ccba4d5cbeade9c48f857f60"
                },
                "cited_as": "L Fejerman"
            }, {
                "name": "M L Neuhouser",
                "@type": "person",
                "@id": "_:e5930003ef914b9e99892cbb134ab0ad"
            }, {
                "order_cited": 10,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:b1fd726a4788423eb3a71509b2493757",
                "agent": {
                    "@type": "person",
                    "@id": "_:e5930003ef914b9e99892cbb134ab0ad"
                },
                "cited_as": "M L Neuhouser"
            }, {
                "name": "C S Carlson",
                "@type": "person",
                "@id": "_:a021013c285a4c589b5c1360eb261647"
            }, {
                "order_cited": 11,
                "@type": "Creator",
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@id": "_:34c8ec8f32a74abbaa38d5efec6e9fdd",
                "agent": {
                    "@type": "person",
                    "@id": "_:a021013c285a4c589b5c1360eb261647"
                },
                "cited_as": "C S Carlson"
            }, {
                "name": "Nature Publishing Group",
                "@type": "organization",
                "@id": "_:2cb215bb499844cf8aecc2c9f817386c"
            }, {
                "agent": {
                    "@type": "organization",
                    "@id": "_:2cb215bb499844cf8aecc2c9f817386c"
                },
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@type": "Publisher",
                "@id": "_:5e65f7f40b0f41989566fcf66241767c"
            }, {
                "name": "ejcn",
                "@type": "Tag",
                "@id": "_:a9d049bdd4c7482bb82f513e09365c2e"
            }, {
                "tag": {
                    "@type": "Tag",
                    "@id": "_:a9d049bdd4c7482bb82f513e09365c2e"
                },
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@type": "ThroughTags",
                "@id": "_:e70071583d604be2a7e104cd61b2b6cc"
            }, {
                "name": "Original Article",
                "@type": "Tag",
                "@id": "_:610d99b2c5b74a82896c4681c60ecebb"
            }, {
                "tag": {
                    "@type": "Tag",
                    "@id": "_:610d99b2c5b74a82896c4681c60ecebb"
                },
                "creative_work": {
                    "@type": "article",
                    "@id": "_:703a584afb704403bc99d684e0914c06"
                },
                "@type": "ThroughTags",
                "@id": "_:eeeef1b6c0c24bc58344938badafd464"
            }, {
                "date_updated": "2016-12-14T00:00:00+00:00",
                "rights": "\u00a9 2016 Macmillan Publishers Limited, part of Springer Nature.",
                "related_works": [],
                "title": "Genetic ancestry in relation to the metabolic response to a US versus traditional Mexican diet: a randomized crossover feeding trial among women of Mexican descent",
                "subjects": [],
                "extra": {
                    "language": "en",
                    "set_spec": "ejcn",
                    "identifiers": [
                        "doi:10.1038/ejcn.2016.211",
                        "oai:nature.com:10.1038/ejcn.2016.211"
                    ],
                    "dates": "2016-12-14",
                    "creator": [
                        "M Santiago-Torres",
                        "J De Dieu Tapsoba",
                        "M Kratz",
                        "J W Lampe",
                        "K L Breymeyer",
                        "L Levy",
                        "X Song",
                        "A Villase\u00f1or",
                        "C-Y Wang",
                        "L Fejerman",
                        "M L Neuhouser",
                        "C S Carlson"
                    ],
                    "resource_type": "Original Article"
                },
                "@id": "_:703a584afb704403bc99d684e0914c06",
                "@type": "article"
            }]
        }


Code Examples
~~~~~~~~~~~~~

    Python

    .. code-block:: python

        import requests

        url = 'https://share.osf.io/api/normalizeddata/'

        payload = {
            'data': {
                'type': 'NormalizedData'
                'attributes': {
                    'data': {
                        '@graph': [{
                            '@type': creativework,
                            '@id': <_:random>,
                            title: "Example Title of Work"
                        }]
                    }
                }
            }
        }

        r = requests.post(url, json=payload, headers={
            'Authorization': 'Bearer <YOUR_TOKEN>',
            'Content-Type': 'application/vnd.api+json'
        })


    JavaScript

    .. code-block:: javascript

        let payload = {
            'data': {
                'type': 'NormalizedData'
                'attributes': {
                    'data': {
                        '@graph': [{
                            '@type': creativework,
                            '@id': <_:random>,
                            title: "Example Title of Work"
                        }]
                    }
                }
            }
        }

        $.ajax({
            method: 'POST',
            headers: {
                'X-CSRFTOKEN': csrfToken
            },
            xhrFields: {
                withCredentials: true,
            },
            data: JSON.stringify(payload),
            contentType: 'application/vnd.api+json',
            url: 'https://share.osf.io/api/normalizeddata/',
        })


.. _browsable SHARE API docs: https://share.osf.io/api/

.. _normalizeddata endpoint: https://share.osf.io/api/normalizeddata

.. _SHARE type: https://share.osf.io/api/v2/schema

.. _SHARE website: https://share.osf.io

.. _OAuth2: http://self-issued.info/docs/draft-ietf-oauth-v2-bearer.html

.. _JSON-API: http://jsonapi.org/

.. _JSON schema: http://json-schema.org/

.. _JSON-LD graphs: https://www.w3.org/TR/json-ld/#named-graphs

.. _JSON-LD nodes: https://www.w3.org/TR/json-ld/#dfn-node

.. _blank node identifier: https://www.w3.org/TR/rdf11-concepts/#dfn-blank-node-identifier

.. _JSON-API paging spec: http://jsonapi.org/format/#fetching-pagination
