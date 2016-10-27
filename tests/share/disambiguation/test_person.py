import pytest

from share.models import AgentIdentifier, Person
from share.disambiguation import AbstractAgentDisambiguator


class TestPerson:

    @pytest.mark.django_db
    def test_does_not_disambiguate_without_identifier(self, john_doe):
        disPerson = AbstractAgentDisambiguator('_:', {'family_name': 'Doe', 'given_name': 'John'}, Person).find()
        assert disPerson is None

    @pytest.mark.django_db
    def test_identifier_disambiguates(self, jane_doe, change_ids):
        identifier = AgentIdentifier.objects.create(
            uri='http://osf.io/jane',
            agent=jane_doe,
            agent_version=jane_doe.versions.first(),
            change_id=change_ids.get())

        disPerson = AbstractAgentDisambiguator('_:', {'identifiers': [identifier.pk]}, Person).find()

        assert disPerson == jane_doe


class TestAffiliations:

    def test_handles_unique_violations(self):
        pass
