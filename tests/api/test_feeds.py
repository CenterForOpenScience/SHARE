import pytest

import faker

from lxml import etree

from share.util.graph import MutableGraph

from tests.share.normalize import factories as f


fake = faker.Faker()
NAMESPACES = {'atom': 'http://www.w3.org/2005/Atom'}


# TODO add tests for RSS


class TestFeed:

    @pytest.fixture()
    def fake_items(self, index_records):
        records = [
            f.CreativeWork(
                identifiers=[f.WorkIdentifier()],
                agent_relations=[
                    f.Creator(),
                    f.Creator(),
                ],
            )
            for i in range(11)
        ]
        return index_records(records)

    def test_atom(self, client, fake_items):
        resp = client.get('/api/v2/feeds/atom')
        assert resp.status_code == 200

        feed = etree.fromstring(resp.content)

        assert len(feed.xpath('//atom:entry', namespaces=NAMESPACES)) == 11
        assert feed.nsmap == {None: 'http://www.w3.org/2005/Atom'}
        assert feed.getchildren()[0].text.startswith('SHARE: Atom feed for query:')

        expected_graphs = [
            MutableGraph.from_jsonld(normd.data)
            for normd in fake_items
        ]
        expected_titles = set(
            gr.get_central_node(guess=True)['title']
            for gr in expected_graphs
        )
        actual_titles = set(
            element.text
            for element in feed.xpath('//atom:entry/atom:title', namespaces=NAMESPACES)
        )
        assert len(actual_titles) == 11
        assert actual_titles == expected_titles


@pytest.mark.parametrize('feed_url, expected_status', [
    ('/api/v2/atom/', 410),
    ('/api/v2/rss/', 410),
    ('/api/v2/feeds/atom/', 200),
    ('/api/v2/feeds/rss/', 200),
])
def test_gone(client, settings, feed_url, expected_status):
    resp = client.get(feed_url)
    assert resp.status_code == expected_status
