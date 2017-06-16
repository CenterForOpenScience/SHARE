import pytest

import pendulum

from elasticsearch.exceptions import NotFoundError

from share import models
from share.util import IDObfuscator
from bots.elasticsearch import tasks

from tests import factories


@pytest.mark.django_db
class TestElasticSearchBot:

    @pytest.fixture(autouse=True)
    def elastic(self, elastic):
        return elastic

    def test_index(self, elastic):
        x = factories.AbstractCreativeWorkFactory()
        source = factories.SourceFactory()
        x.sources.add(source.user)

        tasks.index_model('creativework', [x.id])

        doc = elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(x))

        assert doc['_id'] == IDObfuscator.encode(x)
        assert doc['_source']['title'] == x.title
        assert doc['_source']['sources'] == [source.long_title]

    def test_is_deleted_gets_removed(self, elastic):
        x = factories.AbstractCreativeWorkFactory()
        source = factories.SourceFactory()
        x.sources.add(source.user)

        tasks.index_model('creativework', [x.id])
        elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(x))

        x.administrative_change(is_deleted=True)

        tasks.index_model('creativework', [x.id])

        with pytest.raises(NotFoundError):
            elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(x))

    def test_source_soft_deleted(self, elastic):
        x = factories.AbstractCreativeWorkFactory()
        source = factories.SourceFactory(is_deleted=True)
        x.sources.add(source.user)

        tasks.index_model('creativework', [x.id])

        doc = elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(x))

        assert doc['_id'] == IDObfuscator.encode(x)
        assert doc['_source']['title'] == x.title
        assert doc['_source']['sources'] == []

    def test_51_identifiers_rejected(self, elastic):
        work1 = factories.AbstractCreativeWorkFactory()
        work2 = factories.AbstractCreativeWorkFactory()
        for i in range(50):
            factories.WorkIdentifierFactory(uri='http://example.com/{}'.format(i), creative_work=work1)
            factories.WorkIdentifierFactory(uri='http://example.com/{}/{}'.format(i, i), creative_work=work2)
        factories.WorkIdentifierFactory(creative_work=work2)

        tasks.index_model('creativework', [work1.id, work2.id])

        elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(work1))

        with pytest.raises(NotFoundError):
            elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(work2))

    def test_aggregation(self, elastic):
        work = factories.AbstractCreativeWorkFactory()

        sources = [factories.SourceFactory() for _ in range(4)]
        work.sources.add(*[s.user for s in sources])

        tasks.index_model('creativework', [work.id])

        elastic.es_client.indices.refresh(index=elastic.es_index)

        resp = elastic.es_client.search(index=elastic.es_index, doc_type='creativeworks', body={
            'size': 0,
            'aggregations': {
                'sources': {
                    'terms': {'field': 'sources', 'size': 500}
                }
            }
        })

        assert sorted(resp['aggregations']['sources']['buckets'], key=lambda x: x['key']) == sorted([{'key': source.long_title, 'doc_count': 1} for source in sources], key=lambda x: x['key'])


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
        x = factories.AbstractCreativeWorkFactory()
        source = factories.SourceFactory()
        x.sources.add(source.user)

        y = factories.AbstractCreativeWorkFactory()
        source = factories.SourceFactory()
        y.sources.add(source.user)

        tasks.elasticsearch_janitor()

        assert elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(x))['found'] is True
        assert elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(y))['found'] is True

    def test_date_created(self, elastic, no_celery):
        fake, real = [], []
        models.AbstractCreativeWork._meta.get_field('date_created').auto_now_add = False

        for i in range(1, 6):
            fake.append(factories.AbstractCreativeWorkFactory(
                date_created=pendulum.now(),
                date_modified=pendulum.now(),
            ))
            real.append(factories.AbstractCreativeWorkFactory(
                date_created=pendulum.now().add(days=-i),
                date_modified=pendulum.now().add(days=-i),
            ))
        real.append(factories.AbstractCreativeWorkFactory(
            date_created=pendulum.now().add(days=-i),
            date_modified=pendulum.now().add(days=-i),
        ))

        models.AbstractCreativeWork._meta.get_field('date_created').auto_now_add = True

        tasks.index_model('creativework', [c.id for c in fake])

        for c in fake:
            assert elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(c))['found'] is True
            c.administrative_change(is_deleted=True)

        tasks.elasticsearch_janitor()

        for c in real:
            assert elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(c))['found'] is True
