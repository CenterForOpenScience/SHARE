import json
import pytest

from share.legacy_normalize.transform.chain import ctx
from share.legacy_normalize.transformers.v1_push import V1Transformer


class TestV1Transformer:

    @pytest.mark.parametrize('input, expected', [
        ({
            "contributors": [{
                "name": "Roger Movies Ebert",
                "sameAs": ["https://osf.io/thing"],
                "familyName": "Ebert",
                "givenName": "Roger",
                "additionalName": "Danger",
                "email": "rogerebert@example.com"
            }, {
                "name": "Roger Madness Ebert"
            }],
            "languages": ["eng"],
            "description": "This is a thing",
            "providerUpdatedDateTime": "2014-12-12T00:00:00Z",
            "freeToRead": {
                "startDate": "2014-09-12",
                "endDate": "2014-10-12"
            },
            "licenses": [{
                "uri": "http://www.mitlicense.com",
                "startDate": "2014-10-12T00:00:00Z",
                "endDate": "2014-11-12T00:00:00Z"
            }],
            "publisher": {
                "name": "Roger Ebert Inc",
                "email": "roger@example.com"
            },
            "sponsorships": [{
                "award": {
                    "awardName": "Participation",
                    "awardIdentifier": "http://example.com"
                },
                "sponsor": {
                    "sponsorName": "Orange",
                    "sponsorIdentifier": "http://example.com/orange"
                }
            }],
            "title": "Interesting research",
            "version": {"versionId": "someID"},
            "uris": {
                "canonicalUri": "http://example.com/document1",
                "providerUris": [
                    "http://example.com/document1uri1",
                    "http://example.com/document1uri2"
                ]
            }
        }, {
            '@type': 'creativework',
            'date_updated': '2014-12-12T00:00:00+00:00',
            'description': 'This is a thing',
            'language': 'eng',
            'identifiers': [
                {'@type': 'workidentifier', 'uri': 'http://example.com/document1'},
                {'@type': 'workidentifier', 'uri': 'http://example.com/document1uri1'},
                {'@type': 'workidentifier', 'uri': 'http://example.com/document1uri2'},
            ],
            'related_agents': [{
                '@type': 'creator',
                'cited_as': 'Roger Movies Ebert',
                'order_cited': 0,
                'agent': {
                    '@type': 'person',
                    'name': 'Roger Movies Ebert',
                    'related_agents': [],
                    'identifiers': [
                        {'@type': 'agentidentifier', 'uri': 'http://osf.io/thing'},
                        {'@type': 'agentidentifier', 'uri': 'mailto:rogerebert@example.com'}
                    ],
                },
            }, {
                '@type': 'creator',
                'cited_as': 'Roger Madness Ebert',
                'order_cited': 1,
                'agent': {
                    '@type': 'person',
                    'name': 'Roger Madness Ebert',
                    'related_agents': [],
                    'identifiers': []
                }
            }, {
                '@type': 'publisher',
                'cited_as': 'Roger Ebert Inc',
                'agent': {
                    '@type': 'organization',
                    'name': 'Roger Ebert Inc',
                    'related_agents': [],
                    'identifiers': [
                        {'@type': 'agentidentifier', 'uri': 'mailto:roger@example.com'},
                    ]
                }
            }, {
                '@type': 'funder',
                'awards': [
                    {
                        '@type': 'throughawards',
                        'award': {'@type': 'award', 'name': 'Participation', 'uri': 'http://example.com'}
                    }
                ],
                'cited_as': 'Orange',
                'agent': {
                    '@type': 'organization',
                    'name': 'Orange',
                    'identifiers': [
                        {'@type': 'agentidentifier', 'uri': 'http://example.com/orange'},
                    ]
                }
            }],
            'subjects': [],
            'tags': [],
            'title': 'Interesting research',
        }), ({
            "contributors": [],
            "languages": ["eng"],
            "description": "This is a thing",
            "providerUpdatedDateTime": "2014-12-12T00:00:00Z",
            "title": "Interesting research",
            "uris": {
                "canonicalUri": "http://example.com/document1",
                "providerUris": [
                    "http://example.com/document1uri1",
                    "http://example.com/document1uri2",
                    "http://example.com/document1uri2",
                    'http://example.com/document1',
                ]
            }
        }, {
            '@type': 'creativework',
            'date_updated': '2014-12-12T00:00:00+00:00',
            'description': 'This is a thing',
            'language': 'eng',
            'identifiers': [
                {'@type': 'workidentifier', 'uri': 'http://example.com/document1'},
                {'@type': 'workidentifier', 'uri': 'http://example.com/document1uri1'},
                {'@type': 'workidentifier', 'uri': 'http://example.com/document1uri2'},
            ],
            'related_agents': [],
            'subjects': [],
            'tags': [],
            'title': 'Interesting research',
        }), ({
            "contributors": [],
            "languages": ["eng"],
            "description": "This is a thing",
            "providerUpdatedDateTime": "2014-12-12T00:00:00Z",
            "title": "Interesting research",
            "otherProperties": [{"name": "status", "properties": {"status": "deleted"}}],
            "uris": {
                "canonicalUri": "http://example.com/document1",
                "providerUris": [
                    'http://example.com/document1',
                    "http://example.com/document1uri1",
                    "http://example.com/document1uri2",
                    "http://example.com/document1uri2",
                ]
            }
        }, {
            '@type': 'creativework',
            'date_updated': '2014-12-12T00:00:00+00:00',
            'description': 'This is a thing',
            'is_deleted': True,
            'language': 'eng',
            'identifiers': [
                {'@type': 'workidentifier', 'uri': 'http://example.com/document1'},
                {'@type': 'workidentifier', 'uri': 'http://example.com/document1uri1'},
                {'@type': 'workidentifier', 'uri': 'http://example.com/document1uri2'},
            ],
            'related_agents': [],
            'subjects': [],
            'tags': [],
            'title': 'Interesting research',
        })
    ])
    def test_normalize(self, input, expected):
        ctx.clear()
        _, root_ref = V1Transformer({}).do_transform(json.dumps(input), clean_up=False)
        actual = self.reconstruct(ctx.pool.pop(root_ref))
        assert expected == actual

    def reconstruct(self, document, extra=False):
        for key, val in tuple(document.items()):
            if isinstance(val, dict) and key != 'extra':
                related = ctx.pool.pop(val, None)
                if related:
                    document[key] = self.reconstruct(related, extra=extra)
                else:
                    document.pop(key)
            if isinstance(val, list):
                document[key] = [self.reconstruct(ctx.pool.pop(v), extra=extra) for v in val]
        del document['@id']
        if not extra:
            document.pop('extra', None)
        return document
