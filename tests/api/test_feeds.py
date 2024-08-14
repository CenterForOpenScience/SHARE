import json
from unittest import mock

import pytest
import faker
from lxml import etree

from share.metadata_formats.sharev2_elastic import ShareV2ElasticFormatter

from tests.factories import NormalizedDataFactory, RawDatumFactory
from tests.share.normalize import factories as f


fake = faker.Faker()
NAMESPACES = {'atom': 'http://www.w3.org/2005/Atom'}


# TODO add tests for RSS


@pytest.mark.django_db
class TestFeed:

    @pytest.fixture()
    def fake_items(self, Graph):
        records = [
            Graph(f.CreativeWork(
                title=f'my fabulous work {i}',
                identifiers=[f.WorkIdentifier()],
                agent_relations=[
                    f.Creator(),
                    f.Creator(),
                ],
            )).to_jsonld()
            for i in range(11)
        ]
        normds = [
            NormalizedDataFactory(
                data=record,
                raw=RawDatumFactory(
                    datum='',
                ),
            )
            for record in records
        ]
        formatter = ShareV2ElasticFormatter()
        formatted_items = [
            formatter.format(normd)
            for normd in normds
        ]
        json_items = [
            json.loads(formatted_item)
            for formatted_item in formatted_items
        ]
        with mock.patch('api.views.feeds.index_strategy.get_index_for_sharev2_search') as mock_get_for_searching:
            mock_strategy = mock_get_for_searching.return_value
            mock_strategy.pls_handle_search__sharev2_backcompat.return_value = {
                'hits': {
                    'hits': [
                        {'_source': item, '_id': item['id']}
                        for item in json_items
                    ],
                },
            }
            yield json_items

    def test_atom(self, client, fake_items):
        resp = client.get('/api/v2/feeds/atom')
        assert resp.status_code == 200
        feed = etree.fromstring(resp.content)
        assert len(feed.xpath('//atom:entry', namespaces=NAMESPACES)) == 11
        assert feed.nsmap == {None: 'http://www.w3.org/2005/Atom'}
        assert feed.getchildren()[0].text.startswith('SHARE: Atom feed for query:')
        expected_titles = set(
            item['title']
            for item in fake_items
        )
        actual_titles = set(
            element.text
            for element in feed.xpath('//atom:entry/atom:title', namespaces=NAMESPACES)
        )
        assert actual_titles == expected_titles
        assert len(actual_titles) == 11

    def test_gone(self, client, fake_items):
        for feed_url, expected_status in (
            ('/api/v2/atom/', 410),
            ('/api/v2/rss/', 410),
            ('/api/v2/feeds/atom/', 200),
            ('/api/v2/feeds/rss/', 200),
        ):
            resp = client.get(feed_url)
            assert resp.status_code == expected_status
