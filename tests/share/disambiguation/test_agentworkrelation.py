import pytest

from share import models
from tests.share.models import factories
from share.disambiguation import AgentWorkRelationDisambiguator


@pytest.mark.django_db
class TestDisambiguateCreator:

    def test_all_fields(self):
        work = factories.PreprintFactory(contributors=3)
        contrib = work.agent_relations.first()
        agent = contrib.agent

        assert contrib == AgentWorkRelationDisambiguator('_:', {
            'creative_work': work.id,
            'agent': agent.id,
            'type': contrib.type,
        }, models.AgentWorkRelation).find()

    def test_only_creativework(self):
        work = factories.PreprintFactory(contributors=3)

        assert None is AgentWorkRelationDisambiguator('_:', {
            'creative_work': work.id,
        }, models.AgentWorkRelation).find()

    def test_cited_as(self):
        work = factories.PreprintFactory()
        person = factories.AgentFactory(type='share.person')
        contrib = factories.AgentWorkRelationFactory(creative_work=work, agent=person, type='share.creator')

        assert contrib == AgentWorkRelationDisambiguator('_:', {
            'creative_work': work.id,
            'cited_as': contrib.cited_as,
        }, models.AgentWorkRelation).find()

    def test_cited_as_type(self):
        work = factories.PreprintFactory()
        person = factories.AgentFactory(type='share.person')
        contrib = factories.AgentWorkRelationFactory(creative_work=work, agent=person, type='share.creator')

        assert contrib == AgentWorkRelationDisambiguator('_:', {
            'cited_as': contrib.cited_as,
            'creative_work': work.id,
            'type': contrib.type
        }, models.AgentWorkRelation).find()

    def test_cited_as_type_mismatch(self):
        work = factories.PreprintFactory()
        person = factories.AgentFactory(type='share.person')
        contrib = factories.AgentWorkRelationFactory(creative_work=work, agent=person, type='share.creator')

        assert None is AgentWorkRelationDisambiguator('_:', {
            'cited_as': contrib.cited_as,
            'creative_work': work.id,
            'type': 'share.publisher'
        }, models.AgentWorkRelation).find()

    def test_differing_type(self):
        work = factories.PreprintFactory()
        person = factories.AgentFactory(type='share.person')
        factories.AgentWorkRelationFactory(creative_work=work, agent=person, type='share.creator')

        assert None is AgentWorkRelationDisambiguator('_:', {
            'agent': person.id,
            'creative_work': work.id,
            'type': 'share.publisher'
        }, models.AgentWorkRelation).find()

    def test_no_creative_work(self):
        work = factories.PreprintFactory()
        person = factories.AgentFactory(type='share.person')
        contrib = factories.AgentWorkRelationFactory(creative_work=work, agent=person, type='share.creator')

        assert None is AgentWorkRelationDisambiguator('_:', {
            'cited_as': contrib.cited_as,
            'creative_work': work.id,
            'type': 'share.publisher'
        }, models.AgentWorkRelation).find()

    def test_upgrade_existing_type(self):
        pass

    def test_upgrade_input_type(self):
        pass
