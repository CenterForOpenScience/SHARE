import json
import pytest

from share.normalize import ctx
from share.normalize.v1_push import V1Normalizer


class TestV1Normalizer:

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
            'awards': [],
            'contributors': [{
                '@type': 'person',
                'additional_name': 'Movies',
                'affiliations': [],
                'emails': [{'@type': 'email', 'email': 'rogerebert@example.com'}],
                'family_name': 'Ebert',
                'given_name': 'Roger',
                'identifiers': [{'@type': 'identifier', 'url': 'https://osf.io/thing'}],
                'suffix': ''
            }, {
                '@type': 'person',
                'additional_name': 'Madness',
                'affiliations': [],
                'emails': [],
                'family_name': 'Ebert',
                'given_name': 'Roger',
                'identifiers': [],
                'suffix': ''
            }],
            'date_updated': '2014-12-12T00:00:00+00:00',
            'description': 'This is a thing',
            'funders': [],
            'institutions': [],
            'language': 'eng',
            'links': [
                {'@type': 'link', 'type': 'provider', 'url': 'http://example.com/document1'},
                {'@type': 'link', 'type': 'provider', 'url': 'http://example.com/document1uri1'},
                {'@type': 'link', 'type': 'provider', 'url': 'http://example.com/document1uri2'},
            ],
            'organizations': [],
            'publishers': [{'@type': 'publisher', 'name': 'Roger Ebert Inc'}],
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
            'awards': [],
            'contributors': [],
            'date_updated': '2014-12-12T00:00:00+00:00',
            'description': 'This is a thing',
            'funders': [],
            'institutions': [],
            'language': 'eng',
            'links': [
                {'@type': 'link', 'type': 'provider', 'url': 'http://example.com/document1'},
                {'@type': 'link', 'type': 'provider', 'url': 'http://example.com/document1uri1'},
                {'@type': 'link', 'type': 'provider', 'url': 'http://example.com/document1uri2'},
            ],
            'organizations': [],
            'publishers': [],
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
            'awards': [],
            'contributors': [],
            'date_updated': '2014-12-12T00:00:00+00:00',
            'description': 'This is a thing',
            'funders': [],
            'institutions': [],
            'is_deleted': True,
            'language': 'eng',
            'links': [
                {'@type': 'link', 'type': 'provider', 'url': 'http://example.com/document1'},
                {'@type': 'link', 'type': 'provider', 'url': 'http://example.com/document1uri1'},
                {'@type': 'link', 'type': 'provider', 'url': 'http://example.com/document1uri2'},
            ],
            'organizations': [],
            'publishers': [],
            'subjects': [],
            'tags': [],
            'title': 'Interesting research',
        })
    ])
    def test_normalize(self, input, expected):
        ctx.clear()
        assert expected == self.reconstruct(ctx.pool[V1Normalizer({}).do_normalize(json.dumps(input))])

    def reconstruct(self, document, extra=False):
        for key, val in tuple(document.items()):
            if isinstance(val, dict) and key != 'extra':
                document[key] = self.reconstruct(ctx.pool.pop(val), extra=extra)
            if isinstance(val, list):
                _v = []
                for v in val:
                    through = ctx.pool.pop(v)
                    _v.append(self.reconstruct(ctx.pool.pop(next(x for x in through.values() if isinstance(x, dict) and x['@id'] != document['@id'])), extra=extra))
                document[key] = _v
        del document['@id']
        if not extra:
            document.pop('extra', None)
        return document
