import json
import re

import pytest

import kombu

from django.conf import settings

from share import models
from share import util
from share.search import fetchers
from share.search.messages import V1Message, V2Message, IndexableMessage

from tests import factories


@pytest.mark.skip
class TestIndexableMessage:

    VERSION_MAP = {
        # 0: V0Message,
        1: V1Message,
        2: V2Message,
    }

    @pytest.fixture(params=[
        # (0, models.CreativeWork, [], {'version': 0, 'CreativeWork': []}),
        # (0, models.CreativeWork, [], {'CreativeWork': []}),
        # (0, models.CreativeWork, [1, 2, 3, 4], {'CreativeWork': [1, 2, 3, 4]}),
        # (0, models.Agent, [], {'Agent': []}),
        # (0, models.Agent, [], {'Person': []}),
        # (0, models.Agent, [], {'share.AbstractAgent': []}),
        # (0, models.Tag, [1], {'tag': [1]}),
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
        message = IndexableMessage.wrap(message)

        assert list(message) == self.EXPECTED_IDS
        assert message.model == self.EXPECTED_MODEL
        assert message.PROTOCOL_VERSION == self.EXPECTED_VERSION
        assert isinstance(message, self.VERSION_MAP[self.EXPECTED_VERSION])

    @pytest.mark.parametrize('version', [30, 10, None, 'Foo', '1', '0', {}, []])
    def test_invalid_version(self, version):
        with pytest.raises(ValueError) as e:
            IndexableMessage.wrap(kombu.Message(
                content_type='application/json',
                body=json.dumps({'version': version}),
            ))
        assert e.value.args == ('Invalid version "{}"'.format(version), )


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

        for work in works[:-1]:
            factories.WorkIdentifierFactory(creative_work=work)

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

            'is_deleted': work.is_deleted or not work.identifiers.exists(),
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
    def test_lineage_indexing(self):
        child = factories.AbstractCreativeWorkFactory()

        fetched = next(fetchers.CreativeWorkFetcher()([child.id]))
        assert fetched['lists'].get('lineage') is None

        actual_lineage = [child]
        for _ in range(5):
            new_parent = factories.AbstractCreativeWorkFactory()
            factories.AbstractWorkRelationFactory(
                type='share.ispartof',
                subject=actual_lineage[0],
                related=new_parent
            )
            actual_lineage.insert(0, new_parent)

            for i, work in enumerate(actual_lineage):
                expected_lineage = actual_lineage[:i][-3:]
                fetched = next(fetchers.CreativeWorkFetcher()([work.id]))
                fetched_lineage = fetched['lists'].get('lineage', [])

                assert len(fetched_lineage) == len(expected_lineage)
                for indexed, ancestor in zip(fetched_lineage, expected_lineage):
                    assert indexed['id'] == util.IDObfuscator.encode(ancestor)
                    assert indexed['title'] == ancestor.title
                    assert set(indexed['identifiers']) == set(ancestor.identifiers.values_list('uri'))

    @pytest.mark.django_db
    def test_agent_fetcher(self):
        agents = [
            factories.AbstractAgentFactory(),
            factories.AbstractAgentFactory(),
            factories.AbstractAgentFactory(),
            factories.AbstractAgentFactory(),
        ]

        list(fetchers.AgentFetcher()(agent.id for agent in agents))
