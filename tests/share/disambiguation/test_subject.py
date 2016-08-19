import pytest

from share.models import Subject
from share.models.meta import ThroughSubjects
from share.disambiguation import disambiguate


def create_subject(name):
    Subject.objects.bulk_create([
        Subject(name=name, lineages=[])
    ])
    return Subject.objects.get(name=name)


class TestSubject:

    @pytest.mark.django_db
    def test_disambiguates(self):
        oldSubject = create_subject('This')
        disSubject = disambiguate('_:', {'name': 'This'}, Subject)

        assert disSubject is not None
        assert disSubject.id == oldSubject.id
        assert disSubject.name == oldSubject.name

    @pytest.mark.django_db
    def test_does_not_disambiguate(self):
        oldSubject = create_subject('This')
        disSubject = None
        try:
            disSubject = disambiguate('_:', {'name': 'That'}, Subject)
            assert False
        except:
            assert disSubject is None
