SHARE API
=========

Checkout the `SHARE API docs`_.

Push data directly into the SHARE database
------------------------------------------

Using the `normalizeddata endpoint`_
"""""""""""""""""""""""""""""""""""""
    - the payload should be in the same format as the body template under the CREATE/UPDATE heading::

           Body (JSON):   {
            'data': {
                'type': 'NormalizedData'
                'attributes': {
                    'data': {
                        '@graph': [{
                            '@type': <type of document, exp: person>,
                            '@id': <_:random>,
                            <attribute_name>: <value>,
                            <relationship_name>: {
                                '@type': <type>,
                                '@id': <id>
                            }
                        }]
                    }
                }
            }
           }

    - to create a record, the ``@id`` must be a unique identifier that does not exist in the database
    - to update an existing record, the format remains the same but the existing document will be updated and a new document will not be created
        - versions are kept of every change
    - an `OAuth bearer token`_ is needed to post to the endpoint
        - your token can be obtained by logging in on the `SHARE website`_
    - changesets must be accepted so there will be a delay between submission and public availability

Examples
""""""""

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
            'Authorization': 'TOK:<YOUR_TOKEN>',
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


.. _SHARE API docs: https://share.osf.io/api/

.. _normalizeddata endpoint: https://share.osf.io/api/normalizeddata

.. _SHARE website: https://share.osf.io

.. _OAuth bearer token: http://self-issued.info/docs/draft-ietf-oauth-v2-bearer.html
