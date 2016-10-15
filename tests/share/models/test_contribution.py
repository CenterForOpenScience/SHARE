import pytest

from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from share import models
from tests.share.models import factories


@pytest.mark.django_db
class TestAbstractContribution:

    def test_exists(self):
        x = factories.PreprintFactory(contributions=5)
        assert x.contributors.count() == 5
        for contribution in x.contributions.all():
            assert contribution.creative_work == x
            assert contribution.entity._meta.concrete_model is models.AbstractEntity

    def test_unique(self):
        pp = factories.PreprintFactory()
        person = factories.EntityFactory(type='share.person')
        factories.ContributionFactory(creative_work=pp, entity=person, type='share.collaboratorcontribution')

        with pytest.raises(IntegrityError):
            factories.ContributionFactory(creative_work=pp, entity=person, type='share.collaboratorcontribution')

    def test_many_contribution_types(self):
        pp = factories.PreprintFactory(contributions=0)
        person = factories.EntityFactory(type='share.person')
        funding = factories.ContributionFactory(creative_work=pp, entity=person, type='share.fundercontribution')

        assert pp.contributors.count() == 1

        collaboration = factories.ContributionFactory(creative_work=pp, entity=person, type='share.collaboratorcontribution')

        assert funding != collaboration
        assert pp.contributors.count() == 2


@pytest.mark.django_db
class TestThroughContribution:

    def test_exists(self):
        pp = factories.PreprintFactory(contributions=0)
        person = factories.EntityFactory(type='share.person')
        consortium = factories.EntityFactory(type='share.consortium')
        consortium_collaboration = factories.ContributionFactory(creative_work=pp, entity=consortium, type='share.collaboratorcontribution')
        collaboration = factories.ContributionFactory(creative_work=pp, entity=person, type='share.collaboratorcontribution')
        factories.ThroughContributionFactory(subject=collaboration, related=consortium_collaboration, change=factories.ChangeFactory())

        assert list(collaboration.contributed_through.all()) == [consortium_collaboration]

    def test_must_share_creative_work(self):
        pp1 = factories.PreprintFactory(contributions=0)
        pp2 = factories.PreprintFactory(contributions=0)
        person = factories.EntityFactory(type='share.person')
        consortium = factories.EntityFactory(type='share.consortium')

        consortium_collaboration = factories.ContributionFactory(creative_work=pp1, entity=consortium, type='share.collaboratorcontribution')
        collaboration = factories.ContributionFactory(creative_work=pp2, entity=person, type='share.collaboratorcontribution')

        with pytest.raises(ValidationError) as e:
            factories.ThroughContributionFactory(subject=collaboration, related=consortium_collaboration)
        assert e.value.args == (_('ThroughContributions must contribute to the same AbstractCreativeWork'), None, None)

    def test_cannot_be_self(self):
        pp = factories.PreprintFactory(contributions=0)
        person = factories.EntityFactory(type='share.person')
        collaboration = factories.ContributionFactory(creative_work=pp, entity=person, type='share.collaboratorcontribution')

        with pytest.raises(ValidationError) as e:
            factories.ThroughContributionFactory(subject=collaboration, related=collaboration)
        assert e.value.args == (_('A contributor may not contribute through itself'), None, None)
