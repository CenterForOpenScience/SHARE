import pytest
from datetime import timezone

import faker

from lxml import etree

from share.models import AbstractCreativeWork, AbstractAgentWorkRelation
from share.util import IDObfuscator

from tests import factories


fake = faker.Faker()
NAMESPACES = {'atom': 'http://www.w3.org/2005/Atom'}


# TODO add tests for RSS


@pytest.mark.django_db
class TestFeed:

    @pytest.fixture
    def fake_items(self, settings, index_creativeworks):
        ids = []
        for i in range(11):
            person_0 = factories.AbstractAgentFactory(type='share.person')
            person_1 = factories.AbstractAgentFactory(type='share.person')

            work = factories.AbstractCreativeWorkFactory(
                date_published=None if i % 3 == 0 else fake.date_time_this_decade(tzinfo=timezone.utc),
            )
            if i % 3 == 1:
                factories.CreatorWorkRelationFactory(creative_work=work, agent=person_0, order_cited=0)
                factories.CreatorWorkRelationFactory(creative_work=work, agent=person_1, order_cited=1)
            if i % 3 == 2:
                factories.CreatorWorkRelationFactory(creative_work=work, agent=person_0)

            # Works without identifiers won't be surfaced in search
            factories.WorkIdentifierFactory(creative_work=work)

            ids.append(work.id)

        index_creativeworks(ids)

    @pytest.mark.parametrize('feed_url', [
        '/api/v2/atom/',
        '/api/v2/feeds/atom/',
    ])
    def test_get_feed(self, client, fake_items, feed_url, settings):
        resp = client.get(feed_url)
        assert resp.status_code == 200

        feed = etree.fromstring(resp.content)

        assert len(feed.xpath('//atom:entry', namespaces=NAMESPACES)) == 11
        assert feed.nsmap == {None: 'http://www.w3.org/2005/Atom'}
        assert feed.getchildren()[0].text.startswith('SHARE: Atom feed for query:')

    @pytest.mark.parametrize('order', [
        'date_updated',
        'date_modified',
    ])
    @pytest.mark.parametrize('feed_url', [
        '/api/v2/atom/',
        '/api/v2/feeds/atom/',
    ])
    def test_order(self, client, order, fake_items, feed_url):
        resp = client.get(feed_url, {'order': order})
        assert resp.status_code == 200

        feed = etree.fromstring(resp.content)
        works = AbstractCreativeWork.objects.order_by('-' + order).exclude(**{order: None})

        assert len(feed.xpath('//atom:entry', namespaces=NAMESPACES)) == 11

        for creative_work, entry in zip(works, feed.xpath('//atom:entry', namespaces={'atom': 'http://www.w3.org/2005/Atom'})):
            try:
                contributors = list(AbstractAgentWorkRelation.objects.filter(creative_work_id=creative_work.id))
                first_contributor = AbstractAgentWorkRelation.objects.get(creative_work_id=creative_work.id, order_cited=0)
            except Exception:
                contributors = None

            assert entry.find('atom:title', namespaces=NAMESPACES).text == creative_work.title
            assert entry.find('atom:summary', namespaces=NAMESPACES).text == creative_work.description
            assert entry.find('atom:link', namespaces=NAMESPACES).attrib['href'].endswith(IDObfuscator.encode(creative_work))

            if not contributors:
                assert entry.find('atom:author', namespaces=NAMESPACES)[0].text == 'No authors provided.'
            elif len(contributors) > 1:
                assert entry.find('atom:author', namespaces=NAMESPACES)[0].text == '{} et al.'.format(first_contributor.agent.name)
            else:
                assert entry.find('atom:author', namespaces=NAMESPACES)[0].text == first_contributor.agent.name

            if getattr(creative_work, order):
                assert entry.find('atom:updated', namespaces=NAMESPACES).text == getattr(creative_work, order).replace(microsecond=0).isoformat()
            else:
                assert entry.find('atom:updated', namespaces=NAMESPACES).text is None

            if creative_work.date_published:
                assert entry.find('atom:published', namespaces=NAMESPACES).text == creative_work.date_published.isoformat()
            else:
                assert entry.find('atom:published', namespaces=NAMESPACES) is None

    @pytest.mark.parametrize('feed_url, expected_status', [
        ('/api/v2/atom/', 410),
        ('/api/v2/rss/', 410),
        ('/api/v2/feeds/atom/', 200),
        ('/api/v2/feeds/rss/', 200),
    ])
    def test_gone(self, client, settings, fake_items, feed_url, expected_status):
        settings.SHARE_LEGACY_PIPELINE = False
        resp = client.get(feed_url)
        assert resp.status_code == expected_status
