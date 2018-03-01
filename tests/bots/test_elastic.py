import pytest

import pendulum

from elasticsearch.exceptions import NotFoundError

from share import models
from share.util import IDObfuscator
from bots.elasticsearch import tasks

from tests import factories


def index_helpers(*helpers):
    tasks.index_model('creativework', [h.work.id for h in helpers])


class IndexableWorkTestHelper:
    def __init__(self, elastic, index=False, num_identifiers=1, num_sources=1, date=None):
        self.elastic = elastic

        if date is None:
            self.work = factories.AbstractCreativeWorkFactory()
        else:
            models.AbstractCreativeWork._meta.get_field('date_created').auto_now_add = False
            self.work = factories.AbstractCreativeWorkFactory(
                date_created=date,
                date_modified=date,
            )
            models.AbstractCreativeWork._meta.get_field('date_created').auto_now_add = True

        self.sources = [factories.SourceFactory() for _ in range(num_sources)]
        self.work.sources.add(*[s.user for s in self.sources])

        for i in range(num_identifiers):
            factories.WorkIdentifierFactory(
                uri='http://example.com/{}/{}'.format(self.work.id, i),
                creative_work=self.work
            )

        if index:
            index_helpers(self)

    def assert_indexed(self):
        encoded_id = IDObfuscator.encode(self.work)
        doc = self.elastic.es_client.get(
            index=self.elastic.es_index,
            doc_type='creativeworks',
            id=encoded_id
        )
        assert doc['found'] is True
        assert doc['_id'] == encoded_id
        return doc

    def assert_not_indexed(self):
        with pytest.raises(NotFoundError):
            self.assert_indexed()


@pytest.mark.django_db
class TestElasticSearchBot:

    def test_index(self, elastic):
        helper = IndexableWorkTestHelper(elastic, index=True)
        doc = helper.assert_indexed()
        assert doc['_source']['title'] == helper.work.title
        assert doc['_source']['sources'] == [helper.sources[0].long_title]

    def test_is_deleted_gets_removed(self, elastic):
        helper = IndexableWorkTestHelper(elastic, index=True)
        helper.assert_indexed()

        helper.work.administrative_change(is_deleted=True)
        index_helpers(helper)
        helper.assert_not_indexed()

    def test_source_soft_deleted(self, elastic):
        helper = IndexableWorkTestHelper(elastic, index=True)
        helper.assert_indexed()

        helper.sources[0].is_deleted = True
        helper.sources[0].save()
        index_helpers(helper)

        doc = helper.assert_indexed()
        assert doc['_source']['title'] == helper.work.title
        assert doc['_source']['sources'] == []

    def test_51_identifiers_rejected(self, elastic):
        helper1 = IndexableWorkTestHelper(elastic, index=False, num_identifiers=50)
        helper2 = IndexableWorkTestHelper(elastic, index=False, num_identifiers=51)

        index_helpers(helper1, helper2)

        helper1.assert_indexed()
        helper2.assert_not_indexed()

    def test_aggregation(self, elastic):
        helper = IndexableWorkTestHelper(elastic, index=True, num_sources=4)

        elastic.es_client.indices.refresh(index=elastic.es_index)

        resp = elastic.es_client.search(index=elastic.es_index, doc_type='creativeworks', body={
            'size': 0,
            'aggregations': {
                'sources': {
                    'terms': {'field': 'sources', 'size': 500}
                }
            }
        })

        expected = sorted([{'key': source.long_title, 'doc_count': 1} for source in helper.sources], key=lambda x: x['key'])
        actual = sorted(resp['aggregations']['sources']['buckets'], key=lambda x: x['key'])
        assert expected == actual


@pytest.mark.django_db
class TestIndexSource:

    @pytest.fixture(autouse=True)
    def elastic(self, elastic):
        return elastic

    def test_index(self, elastic):
        source = factories.SourceFactory()

        tasks.index_sources()

        doc = elastic.es_client.get(index=elastic.es_index, doc_type='sources', id=source.name)

        assert doc['_id'] == source.name
        assert doc['_source']['name'] == source.long_title
        assert doc['_source']['short_name'] == source.name

    def test_index_deleted(self, elastic):
        source = factories.SourceFactory(is_deleted=True)

        tasks.index_sources()

        with pytest.raises(NotFoundError):
            elastic.es_client.get(index=elastic.es_index, doc_type='sources', id=source.name)

    def test_index_no_icon(self, elastic):
        source = factories.SourceFactory(icon=None)

        tasks.index_sources()

        with pytest.raises(NotFoundError):
            elastic.es_client.get(index=elastic.es_index, doc_type='sources', id=source.name)


@pytest.mark.django_db
class TestJanitorTask:

    def test_missing_records_get_indexed(self, elastic, monkeypatch, no_celery):
        helper1 = IndexableWorkTestHelper(elastic, index=False)
        helper2 = IndexableWorkTestHelper(elastic, index=False)

        helper1.assert_not_indexed()
        helper2.assert_not_indexed()

        tasks.elasticsearch_janitor(to_daemon=False)

        helper1.assert_indexed()
        helper2.assert_indexed()

    def test_date_created(self, elastic, no_celery):
        fake, real = [], []

        for i in range(1, 6):
            fake.append(IndexableWorkTestHelper(elastic, index=False, date=pendulum.now()))
            real.append(IndexableWorkTestHelper(elastic, index=False, date=pendulum.now().add(days=-i)))
        real.append(IndexableWorkTestHelper(elastic, index=False, date=pendulum.now().add(days=-i)))

        index_helpers(*fake)

        for helper in fake:
            helper.assert_indexed()
            helper.work.administrative_change(is_deleted=True)

        for helper in real:
            helper.assert_not_indexed()

        tasks.elasticsearch_janitor(to_daemon=False)

        for helper in real:
            helper.assert_indexed()
