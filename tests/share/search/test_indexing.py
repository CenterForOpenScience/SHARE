from unittest import mock
import json
import re

import pytest

import kombu

from django.conf import settings

from share import models
from share import util
from share.search import fetchers
from share.search import indexing

from tests import factories


class TestIndexableMessage:

    VERSION_MAP = {
        0: indexing.V0Message,
        1: indexing.V1Message,
    }

    @pytest.fixture(params=[
        (0, models.CreativeWork, [], {'version': 0, 'CreativeWork': []}),
        (0, models.CreativeWork, [], {'CreativeWork': []}),
        (0, models.CreativeWork, [1, 2, 3, 4], {'CreativeWork': [1, 2, 3, 4]}),
        (0, models.Agent, [], {'Agent': []}),
        (0, models.Agent, [], {'Person': []}),
        (0, models.Agent, [], {'share.AbstractAgent': []}),
        (0, models.Tag, [1], {'tag': [1]}),
        (1, models.Tag, [1, 2], {'model': 'Tag', 'ids': [1, 2], 'version': 1}),
    ])
    def message(self, request):
        version, model, ids, payload = request.param

        self.EXPECTED_IDS = ids
        self.EXPECTED_MODEL = model
        self.EXPECTED_VERSION = version

        return kombu.Message(
            content_type='application/json',
            body=json.dumps(payload),
        )

    def test_wrap(self, message):
        message = indexing.IndexableMessage.wrap(message)

        assert list(message) == self.EXPECTED_IDS
        assert message.model == self.EXPECTED_MODEL
        assert message.protocol_version == self.EXPECTED_VERSION
        assert isinstance(message, self.VERSION_MAP[self.EXPECTED_VERSION])

    @pytest.mark.parametrize('version', [30, 10, None, 'Foo', '1', '0', {}, []])
    def test_invalid_version(self, version):
        with pytest.raises(ValueError) as e:
            indexing.IndexableMessage.wrap(kombu.Message(
                content_type='application/json',
                body=json.dumps({'version': version}),
            ))
        assert e.value.args == ('Invalid version "{}"'.format(version), )


class TestMessageFlattener:

    def message_factory(self, model='CreativeWork', ids=None):
        if ids is None:
            ids = [1, 2, 3]

        msg = indexing.IndexableMessage.wrap(kombu.Message(
            content_type='application/json',
            body=json.dumps({model: ids}),
        ))

        msg.message.ack = mock.Mock()
        msg.message.requeue = mock.Mock()

        return msg

    @pytest.mark.parametrize('number', [0, 1, 5])
    def test_len(self, number):
        assert len(indexing.MessageFlattener([self.message_factory() for _ in range(number)])) == number * 3

    def test_list(self):
        assert list(indexing.MessageFlattener([])) == []

        assert list(indexing.MessageFlattener([
            self.message_factory(ids=[1, 2, 3]),
        ])) == [1, 2, 3]

        assert list(indexing.MessageFlattener([
            self.message_factory(ids=[1, 2, 3]),
            self.message_factory(ids=[4]),
            self.message_factory(ids=[]),
            self.message_factory(ids=[]),
            self.message_factory(ids=[]),
            self.message_factory(ids=[5, 6]),
        ])) == [1, 2, 3, 4, 5, 6]

    def test_moves_to_pending(self):
        messages = [
            self.message_factory(ids=[]),
            self.message_factory(ids=[]),
            self.message_factory(ids=[0]),
            self.message_factory(ids=[1, 2]),
            self.message_factory(ids=[3, 4, 5]),
            self.message_factory(ids=[6, 7, 8, 9]),
        ]

        flattener = indexing.MessageFlattener(messages)
        assert list(flattener.pending) == []

        lengths = [3, 3, 4, 4, 4, 5, 5, 5, 5, 6]

        # Forces the initial buffer load.
        # Will always be called in a for loop.
        iter(flattener)

        for i in range(10):
            assert i == next(flattener)
            assert list(flattener.pending) == messages[:lengths[i]]

    def test_ack(self):
        messages = [
            self.message_factory(ids=[]),
            self.message_factory(ids=[]),
            self.message_factory(ids=[0]),
            self.message_factory(ids=[1, 2]),
            self.message_factory(ids=[3, 4, 5]),
            self.message_factory(ids=[6, 7, 8, 9]),
        ]

        flattener = indexing.MessageFlattener(messages)
        assert list(flattener.pending) == []

        lengths = [3, 3, 4, 4, 4, 5, 5, 5, 5, 6]

        # Forces the initial buffer load.
        # Will always be called in a for loop.
        iter(flattener)

        for i in range(10):
            assert i == next(flattener)
            flattener.ack_pending()
            assert list(flattener.pending) == []
            assert list(flattener.requeued) == []
            assert flattener.acked == messages[:lengths[i]]

        for message in messages:
            assert message.message.ack.called

    def test_requeue(self):
        messages = [
            self.message_factory(ids=[]),
            self.message_factory(ids=[]),
            self.message_factory(ids=[0]),
            self.message_factory(ids=[1, 2]),
            self.message_factory(ids=[3, 4, 5]),
            self.message_factory(ids=[6, 7, 8, 9]),
        ]

        flattener = indexing.MessageFlattener(messages)
        assert list(flattener.pending) == []

        lengths = [3, 3, 4, 4, 4, 5, 5, 5, 5, 6]

        # Forces the initial buffer load.
        # Will always be called in a for loop.
        iter(flattener)

        for i in range(10):
            assert i == next(flattener)
            flattener.requeue_pending()
            assert list(flattener.acked) == []
            assert list(flattener.pending) == []
            assert flattener.requeued == messages[:lengths[i]]

        for message in messages:
            assert message.message.requeue.called


class TestFetchers:

    @pytest.mark.parametrize('model, fetcher', [
        (models.Agent, fetchers.AgentFetcher),
        (models.Person, fetchers.AgentFetcher),
        (models.AbstractAgent, fetchers.AgentFetcher),
        (models.Article, fetchers.CreativeWorkFetcher),
        (models.Preprint, fetchers.CreativeWorkFetcher),
        (models.CreativeWork, fetchers.CreativeWorkFetcher),
        (models.AbstractCreativeWork, fetchers.CreativeWorkFetcher),
    ])
    def test_fetcher_for(self, model, fetcher):
        assert isinstance(fetchers.fetcher_for(model), fetcher)

    def test_fetcher_not_found(self):
        with pytest.raises(ValueError) as e:
            fetchers.fetcher_for(models.AgentIdentifier)
        assert e.value.args == ('No fetcher exists for <class \'share.models.identifiers.AgentIdentifier\'>', )

    @pytest.mark.django_db
    @pytest.mark.parametrize('id, type, final_type, types', [
        (12, 'share.agent', 'agent', ['agent']),
        (1850, 'share.Person', 'person', ['agent', 'person']),
        (1850, 'share.Institution', 'institution', ['agent', 'organization', 'institution']),
        (85, 'share.preprint', 'preprint', ['creative work', 'publication', 'preprint']),
        (85, 'share.Software', 'software', ['creative work', 'software']),
    ])
    def test_populate_types(self, id, type, final_type, types):
        fetcher = fetchers.Fetcher()

        populated = fetcher.populate_types({'id': id, 'type': type})

        assert populated['type'] == final_type
        assert populated['types'] == types[::-1]
        assert util.IDObfuscator.decode_id(populated['id']) == id

    @pytest.mark.django_db
    def test_creativework_fetcher(self):
        works = [
            factories.AbstractCreativeWorkFactory(),
            factories.AbstractCreativeWorkFactory(is_deleted=True),
            factories.AbstractCreativeWorkFactory(),
            factories.AbstractCreativeWorkFactory(),
        ]

        factories.WorkIdentifierFactory.create_batch(5, creative_work=works[0])

        source = factories.SourceFactory()
        works[1].sources.add(source.user)

        # Trim trailing zeros
        def iso(x):
            return re.sub(r'(\.\d+?)0*\+', r'\1+', x.isoformat())

        fetched = list(fetchers.CreativeWorkFetcher()(work.id for work in works))

        # TODO add more variance
        assert fetched == [{
            'id': util.IDObfuscator.encode(work),
            'type': work._meta.verbose_name,
            'types': [cls._meta.verbose_name for cls in type(work).mro() if hasattr(cls, '_meta') and cls._meta.proxy],

            'title': work.title,
            'description': work.description,

            'date': iso(work.date_published),
            'date_created': iso(work.date_created),
            'date_modified': iso(work.date_modified),
            'date_published': iso(work.date_published),
            'date_updated': iso(work.date_updated),

            'is_deleted': work.is_deleted,
            'justification': getattr(work, 'justification', None),
            'language': work.language,
            'registration_type': getattr(work, 'registration_type', None),
            'retracted': work.outgoing_creative_work_relations.filter(type='share.retracted').exists(),
            'withdrawn': getattr(work, 'withdrawn', None),

            'identifiers': list(work.identifiers.values_list('uri', flat=True)),
            'sources': [user.source.long_title for user in work.sources.all()],
            'subjects': [],
            'subject_synonyms': [],
            'tags': [],

            'lists': {},
        } for work in works]

    @pytest.mark.django_db
    @pytest.mark.parametrize('bepresses, customs, expected', [
        ([], [-1], {
            'subjects': ['mergik|Magic|Cool Magic|SUPER COOL MAGIC'],
            'subject_synonyms': ['bepress|Engineering|Computer Engineering|Data Storage Systems'],
        }),
        ([-1], [], {
            'subjects': ['bepress|Engineering|Computer Engineering|Data Storage Systems'],
            'subject_synonyms': [],
        }),
        ([-1], [-1], {
            'subjects': ['bepress|Engineering|Computer Engineering|Data Storage Systems', 'mergik|Magic|Cool Magic|SUPER COOL MAGIC'],
            'subject_synonyms': ['bepress|Engineering|Computer Engineering|Data Storage Systems'],
        }),
        ([0, 1], [], {
            'subjects': ['bepress|Engineering', 'bepress|Engineering|Computer Engineering'],
            'subject_synonyms': [],
        }),
        ([], [0, 1], {
            'subjects': ['mergik|Magic', 'mergik|Magic|Cool Magic'],
            'subject_synonyms': ['bepress|Engineering', 'bepress|Engineering|Computer Engineering'],
        }),
    ])
    def test_subject_indexing(self, bepresses, customs, expected):
        custom_tax = factories.SubjectTaxonomyFactory(source__long_title='mergik')
        system_tax = models.SubjectTaxonomy.objects.get(source__user__username=settings.APPLICATION_USERNAME)

        custom = ['Magic', 'Cool Magic', 'SUPER COOL MAGIC']
        bepress = ['Engineering', 'Computer Engineering', 'Data Storage Systems']

        for i, name in enumerate(tuple(bepress)):
            bepress[i] = factories.SubjectFactory(
                name=name,
                taxonomy=system_tax,
                parent=bepress[i - 1] if i > 0 else None,
            )

        for i, name in enumerate(tuple(custom)):
            custom[i] = factories.SubjectFactory(
                name=name,
                taxonomy=custom_tax,
                central_synonym=bepress[i],
                parent=custom[i - 1] if i > 0 else None,
            )

        work = factories.AbstractCreativeWorkFactory()

        for i in bepresses:
            factories.ThroughSubjectsFactory(subject=bepress[i], creative_work=work)
        for i in customs:
            factories.ThroughSubjectsFactory(subject=custom[i], creative_work=work)

        fetched = next(fetchers.CreativeWorkFetcher()([work.id]))
        assert {k: v for k, v in fetched.items() if k.startswith('subject')} == expected

    @pytest.mark.django_db
    def test_agent_fetcher(self):
        agents = [
            factories.AbstractAgentFactory(),
            factories.AbstractAgentFactory(),
            factories.AbstractAgentFactory(),
            factories.AbstractAgentFactory(),
        ]

        list(fetchers.AgentFetcher()(agent.id for agent in agents))


@pytest.mark.django_db
class TestESIndexer:

    @pytest.fixture
    def es_client(self):
        es_c = mock.Mock()
        es_c.cluster.health.return_value = {'status': 'green'}
        return es_c

    @pytest.fixture(autouse=True)
    def ack(self, monkeypatch):
        m = mock.Mock()
        monkeypatch.setattr('kombu.Message.ack', m)
        return m

    @pytest.fixture(autouse=True)
    def sleep(self, monkeypatch):
        m = mock.Mock()
        monkeypatch.setattr('time.sleep', m)
        return m

    def message_factory(self, model='CreativeWork', ids=None):
        if ids is None:
            ids = [1, 2, 3]

        return kombu.Message(
            content_type='application/json',
            body=json.dumps({model: ids}),
        )

    def test_empty(self, es_client):
        indexer = indexing.ESIndexer(es_client, 'share_v1')
        indexer.index()

        indexer = indexing.ESIndexer(es_client, 'share_v1', self.message_factory(ids=[]), self.message_factory('Agent', ids=[]))
        indexer.index()

    def test_indexes(self, elastic):
        messages = [
            self.message_factory(ids=[x.id for x in factories.AbstractCreativeWorkFactory.create_batch(5)]),
            self.message_factory(ids=[x.id for x in factories.AbstractCreativeWorkFactory.create_batch(3)]),
            self.message_factory(ids=[x.id for x in factories.AbstractCreativeWorkFactory.create_batch(8)]),
        ]

        indexer = indexing.ESIndexer(elastic.es_client, settings.ELASTICSEARCH_INDEX, *messages)

        indexer.index()

        elastic.es_client.indices.refresh(elastic.es_index)

        assert elastic.es_client.count(index=elastic.es_index, doc_type='creativeworks')['count'] == 16
        assert set(
            doc['_id'] for doc
            in elastic.es_client.search(doc_type='creativeworks', index=elastic.es_index, _source=['_id'], size=20)['hits']['hits']
        ) == set(util.IDObfuscator.encode(work) for work in models.AbstractCreativeWork.objects.all())

    def test_retries(self, sleep, es_client):
        indexer = indexing.ESIndexer(es_client, settings.ELASTICSEARCH_INDEX)
        indexer._index = mock.Mock()
        indexer._index.side_effect = Exception('Testing')

        with pytest.raises(SystemExit):
            indexer.index()

        assert len(indexer._index.call_args_list) == indexer.MAX_RETRIES
        assert sleep.call_args_list == [mock.call(2 ** (i + 1)) for i in range(indexer.MAX_RETRIES - 1)]

    def test_checks_health(self, es_client):
        indexer = indexing.ESIndexer(es_client, settings.ELASTICSEARCH_INDEX)
        indexer.index()

        assert es_client.cluster.health.called is True

    def test_red_fails(self, es_client):
        es_client.cluster.health.return_value = {'status': 'red'}
        indexer = indexing.ESIndexer(es_client, settings.ELASTICSEARCH_INDEX)

        with pytest.raises(ValueError) as e:
            indexer._index()

        assert e.value.args == ('ES cluster health is red, Refusing to index', )

    def test_gentle_mode(self, es_client):
        es_client.cluster.health.return_value = {'status': 'yellow'}
        indexer = indexing.ESIndexer(es_client, settings.ELASTICSEARCH_INDEX, self.message_factory())
        indexer.bulk_stream = mock.MagicMock()
        indexer._index()

        assert indexer.bulk_stream.assert_called_once_with(models.CreativeWork, mock.ANY, mock.ANY, gentle=True) is None

    @pytest.mark.django_db
    def test_acks(self, elastic):
        messages = [
            self.message_factory(ids=[x.id for x in factories.AbstractCreativeWorkFactory.create_batch(6)]),
            self.message_factory(ids=[x.id for x in factories.AbstractCreativeWorkFactory.create_batch(4)]),
            self.message_factory(ids=[x.id for x in factories.AbstractCreativeWorkFactory.create_batch(8)]),
        ]

        indexer = indexing.ESIndexer(elastic.es_client, settings.ELASTICSEARCH_INDEX, *messages)
        indexer.index()

        for message in messages:
            assert message.ack.called is True
