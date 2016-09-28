import pytest

from share.models import Identifier, Person
from share.models.people import PersonIdentifier
from share.disambiguation import disambiguate


class TestPerson:

    @pytest.mark.django_db
    def test_does_not_disambiguate_without_identifier(self, john_doe):
        disPerson = disambiguate('_:', {'family_name': 'Doe', 'given_name': 'John'}, Person)
        assert disPerson is None

    @pytest.mark.django_db
    def test_identifier_disambiguates(self, jane_doe, change_ids):
        identifier = Identifier.objects.create(url='http://osf.io/jane', change_id=change_ids.get())

        PersonIdentifier.objects.create(
            identifier=identifier,
            person=jane_doe,
            change_id=change_ids.get(),
            identifier_version=identifier.versions.first(),
            person_version=jane_doe.versions.first(),
        )

        assert disambiguate('_:', {'identifiers': [identifier.pk]}, Person) == jane_doe


class TestAffiliations:

    def test_handles_unique_violations(self):
        pass
