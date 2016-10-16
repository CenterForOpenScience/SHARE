import pytest

from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from tests.share.models import factories


@pytest.mark.django_db
class TestAbstractEntityWorkRelation:

    def test_exists(self):
        x = factories.PreprintFactory(contributions=5)
        assert x.related_entities.count() == 5
        for contribution in x.entity_relations.all():
            assert contribution.creative_work == x
            assert list(contribution.entity.related_works.all()) == [x]

    def test_unique(self):
        pp = factories.PreprintFactory()
        person = factories.EntityFactory(type='share.person')
        factories.EntityWorkRelationFactory(creative_work=pp, entity=person, type='share.contribution')

        with pytest.raises(IntegrityError):
            factories.EntityWorkRelationFactory(creative_work=pp, entity=person, type='share.contribution')

    def test_many_contribution_types(self):
        pp = factories.PreprintFactory(contributions=0)
        person = factories.EntityFactory(type='share.person')
        funding = factories.EntityWorkRelationFactory(creative_work=pp, entity=person, type='share.fundingcontribution')

        assert pp.related_entities.count() == 1
        assert pp.entity_relations.count() == 1

        collaboration = factories.EntityWorkRelationFactory(creative_work=pp, entity=person, type='share.contribution')

        assert funding != collaboration
        assert pp.related_entities.count() == 2
        assert pp.entity_relations.count() == 2


@pytest.mark.django_db
class TestThroughEntityWorkRelation:

    def test_exists(self):
        pp = factories.PreprintFactory(contributions=0)
        person = factories.EntityFactory(type='share.person')
        consortium = factories.EntityFactory(type='share.consortium')
        consortium_collaboration = factories.EntityWorkRelationFactory(creative_work=pp, entity=consortium, type='share.contribution')
        collaboration = factories.EntityWorkRelationFactory(creative_work=pp, entity=person, type='share.contribution')
        factories.ThroughEntityWorkRelationFactory(subject=collaboration, related=consortium_collaboration, change=factories.ChangeFactory())

        assert list(collaboration.contributed_through.all()) == [consortium_collaboration]

    def test_must_share_creative_work(self):
        pp1 = factories.PreprintFactory(contributions=0)
        pp2 = factories.PreprintFactory(contributions=0)
        person = factories.EntityFactory(type='share.person')
        consortium = factories.EntityFactory(type='share.consortium')

        consortium_collaboration = factories.EntityWorkRelationFactory(creative_work=pp1, entity=consortium, type='share.contribution')
        collaboration = factories.EntityWorkRelationFactory(creative_work=pp2, entity=person, type='share.contribution')

        with pytest.raises(ValidationError) as e:
            factories.ThroughEntityWorkRelationFactory(subject=collaboration, related=consortium_collaboration)
        assert e.value.args == (_('ThroughContributions must contribute to the same AbstractCreativeWork'), None, None)

    def test_cannot_be_self(self):
        pp = factories.PreprintFactory(contributions=0)
        person = factories.EntityFactory(type='share.person')
        collaboration = factories.EntityWorkRelationFactory(creative_work=pp, entity=person, type='share.contribution')

        with pytest.raises(ValidationError) as e:
            factories.ThroughEntityWorkRelationFactory(subject=collaboration, related=collaboration)
        assert e.value.args == (_('A contributor may not contribute through itself'), None, None)
