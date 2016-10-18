import pytest

from django.core.exceptions import ValidationError

from share.models import Subject
from share.disambiguation import SubjectDisambiguator


def create_subject(name):
    Subject.objects.bulk_create([
        Subject(name=name, lineages=[])
    ])
    return Subject.objects.get(name=name)


class TestSubject:

    @pytest.mark.django_db
    def test_disambiguates(self):
        oldSubject = create_subject('This')
        disSubject = SubjectDisambiguator('_:', {'name': 'This'}, Subject).find()

        assert disSubject is not None
        assert disSubject.id == oldSubject.id
        assert disSubject.name == oldSubject.name

    @pytest.mark.django_db
    def test_does_not_disambiguate(self):
        create_subject('This')

        with pytest.raises(ValidationError) as e:
            SubjectDisambiguator('_:', {'name': 'That'}, Subject).find()

        assert e.value.message == 'Invalid subject: That'
