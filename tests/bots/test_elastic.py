import pytest

from elasticsearch.exceptions import NotFoundError

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

        tasks.IndexModelTask().apply((1, elastic.config.label, 'creativework', [x.id]))

        doc = elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(x))

        assert doc['_id'] == IDObfuscator.encode(x)
        assert doc['_source']['title'] == x.title
        assert doc['_source']['sources'] == [source.long_title]

    def test_is_deleted_gets_removed(self, elastic):
        x = factories.AbstractCreativeWorkFactory()
        source = factories.SourceFactory()
        x.sources.add(source.user)

        tasks.IndexModelTask().apply((1, elastic.config.label, 'creativework', [x.id]))
        elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(x))

        x.administrative_change(is_deleted=True)

        tasks.IndexModelTask().apply((1, elastic.config.label, 'creativework', [x.id]))

        with pytest.raises(NotFoundError):
            elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(x))

    def test_source_soft_deleted(self, elastic):
        x = factories.AbstractCreativeWorkFactory()
        source = factories.SourceFactory(is_deleted=True)
        x.sources.add(source.user)

        tasks.IndexModelTask().apply((1, elastic.config.label, 'creativework', [x.id]))

        doc = elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(x))

        assert doc['_id'] == IDObfuscator.encode(x)
        assert doc['_source']['title'] == x.title
        assert doc['_source']['sources'] == []


@pytest.mark.django_db
class TestIndexSource:

    @pytest.fixture(autouse=True)
    def elastic(self, elastic):
        return elastic

    def test_index(self, elastic):
        source = factories.SourceFactory()

        tasks.IndexSourceTask().apply((1, elastic.config.label))

        doc = elastic.es_client.get(index=elastic.es_index, doc_type='sources', id=source.name)

        assert doc['_id'] == source.name
        assert doc['_source']['name'] == source.long_title
        assert doc['_source']['short_name'] == source.name

    def test_index_deleted(self, elastic):
        source = factories.SourceFactory(is_deleted=True)

        tasks.IndexSourceTask().apply((1, elastic.config.label))

        with pytest.raises(NotFoundError):
            elastic.es_client.get(index=elastic.es_index, doc_type='sources', id=source.name)

    def test_index_no_icon(self, elastic):
        source = factories.SourceFactory(icon=None)

        tasks.IndexSourceTask().apply((1, elastic.config.label))

        with pytest.raises(NotFoundError):
            elastic.es_client.get(index=elastic.es_index, doc_type='sources', id=source.name)

    def test_51_identifiers_rejected(self, elastic):
        work1 = factories.AbstractCreativeWorkFactory()
        work2 = factories.AbstractCreativeWorkFactory()
        for i in range(50):
            factories.WorkIdentifierFactory(uri='http://example.com/{}'.format(i), creative_work=work1)
            factories.WorkIdentifierFactory(uri='http://example.com/{}/{}'.format(i, i), creative_work=work2)
        factories.WorkIdentifierFactory(creative_work=work2)

        tasks.IndexModelTask().apply((1, elastic.config.label, 'creativework', [work1.id, work2.id]))

        elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(work1))

        with pytest.raises(NotFoundError):
            elastic.es_client.get(index=elastic.es_index, doc_type='creativeworks', id=IDObfuscator.encode(work2))
