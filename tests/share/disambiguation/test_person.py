import pytest

from share.models import PersonIdentifier, Person
from share.disambiguation import disambiguate


class TestPerson:

    @pytest.mark.django_db
    def test_does_not_disambiguate_without_identifier(self, john_doe):
        disPerson = disambiguate('_:', {'family_name': 'Doe', 'given_name': 'John'}, Person)
        assert disPerson is None

    @pytest.mark.django_db
    def test_identifier_disambiguates(self, jane_doe, change_ids):
        identifier = PersonIdentifier.objects.create(
            uri='http://osf.io/jane',
            person=jane_doe,
            person_version=jane_doe.versions.first(),
            change_id=change_ids.get())

        assert disambiguate('_:', {'personidentifiers': [identifier.pk]}, Person) == jane_doe


class TestAffiliations:

    def test_handles_unique_violations(self):
        pass
