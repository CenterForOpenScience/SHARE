import json


def get_trove_openapi_json() -> str:
    return json.dumps(get_trove_openapi())


def get_trove_openapi() -> dict:
    return {  # following https://spec.openapis.org/oas/v3.1.0
        'openapi': '3.1.0',
        'info': {
            'title': 'trove: a catalog of index-cards (of rdf metadata)',
            # 'summary': '',
            # 'description': '',
            'termsOfService': 'https://github.com/CenterForOpenScience/cos.io/blob/HEAD/TERMS_OF_USE.md',
            'contact': {
                # 'name':
                # 'url': web-browsable version of this
                'email': 'share-support@osf.io',
            },
            # 'license':
            'version': '23.2.0',
        },
        'servers': [{
            'url': 'https://share.osf.io',
        }],
        'paths': {
            '/trove/index-card-search': {
                'summary': 'search for index-cards that match some iri filters and text',
                # 'description':
                'get': {
                    # 'tags':
                    # 'summary':
                    # 'description':
                    # 'externalDocs':
                    'operationId': 'index-card-search--get',
                    'parameters': [
                        {'$ref': '#/components/parameters/cardSearchText'},
                        {'$ref': '#/components/parameters/cardSearchFilter'},
                        {'$ref': '#/components/parameters/page'},
                        {'$ref': '#/components/parameters/page[size]'},
                        {'$ref': '#/components/parameters/sort'},
                        # {'$ref': '#/components/parameters/include'},
                    ],
                },
            },
            '/trove/index-value-search': {
                'summary': 'search for iri-identified values for specific properties on index-cards that match some iri filters and text',
                # 'description':
                'get': {
                    # 'tags':
                    # 'summary':
                    # 'description':
                    # 'externalDocs':
                    'operationId': 'index-value-search--get',
                    'parameters': [
                        {'$ref': '#/components/parameters/valueSearchPropertyPath'},
                        {'$ref': '#/components/parameters/valueSearchText'},
                        {'$ref': '#/components/parameters/valueSearchFilter'},
                        {'$ref': '#/components/parameters/cardSearchText'},
                        {'$ref': '#/components/parameters/cardSearchFilter'},
                        {'$ref': '#/components/parameters/page'},
                        {'$ref': '#/components/parameters/page[size]'},
                        {'$ref': '#/components/parameters/sort'},
                        # {'$ref': '#/components/parameters/include'},
                    ],
                },
            },
        },
        'components': {
            'parameters': {  # TODO: generate /components/parameters from search_param dataclasses (or vocab)?
                'cardSearchText': {
                    'name': 'cardSearchText',
                    'in': 'query',
                    'required': False,
                    'description': 'TODO',
                },
                'cardSearchFilter': {
                    'name': 'cardSearchFilter[{propertyPaths}][{filterOperation}]',
                    'in': 'query',
                    'required': False,
                    'description': '''
## cardSearchFilter
each query parameter in the *cardSearchFilter* family may exclude index-cards from
the result set based on IRI values at specific locations in the index-card rdf tree.

### propertyPaths

''',
                },
                'valueSearchPropertyPath': {
                    'name': 'valueSearchPropertyPath',
                    'in': 'query',
                    'required': True,
                    'description': 'TODO',
                },
                'valueSearchText': {
                    'name': 'valueSearchText',
                    'in': 'query',
                    'required': False,
                    'description': 'TODO',
                },
                'valueSearchFilter': {
                    'name': 'valueSearchFilter[{propertyPaths}][{filterOperation}]',
                    'in': 'query',
                    'required': False,
                    'description': 'TODO',
                },
                'page': {
                    'name': 'page',
                    'in': 'query',
                    'required': False,
                    'description': 'TODO',
                },
                'page[size]': {
                    'name': 'page[size]',
                    'in': 'query',
                    'required': False,
                    'description': 'TODO',
                },
                'sort': {
                    'name': 'sort',
                    'in': 'query',
                    'required': False,
                    'description': 'TODO',
                },
                # 'include': {
                #     'name': 'include',
                #     'in': 'query',
                #     'required': False,
                #     'description': 'TODO',
                # },
            },
        },
    }
