import pytest

from share.models import CreativeWorkIdentifier, CreativeWork
from share.disambiguation import disambiguate


class TestAbstractWork:

    @pytest.mark.django_db
    def test_does_not_disambiguate_without_identifier(self, change_ids):
        CreativeWork.objects.create(
            title='all about giraffes',
            description='see here is the the thing about giraffes',
            change_id=change_ids.get()
        )
        disWork = disambiguate('_:', {'title': 'all about giraffes'}, CreativeWork)

        assert disWork is None

    @pytest.mark.django_db
    def test_does_not_disambiguate(self, change_ids):
        CreativeWork.objects.create(
            title='all about giraffes',
            description='see here is the the thing about giraffes',
            change_id=change_ids.get()
        )
        disWork = disambiguate('_:', {'title': 'all about short-necked ungulates'}, CreativeWork)

        assert disWork is None

    @pytest.mark.django_db
    def test_does_not_disambiguate_empty_string(self, change_ids):
        CreativeWork.objects.create(
            title='',
            description='see here is the the thing about emptiness',
            change_id=change_ids.get()
        )
        disWork = disambiguate('_:', {'title': ''}, CreativeWork)

        assert disWork is None

    @pytest.mark.django_db
    def test_identifier_disambiguate(self, change_ids):
        cw = CreativeWork.objects.create(
            title='All about cats',
            description='see here is the the thing about emptiness',
            change_id=change_ids.get()
        )

        identifier = CreativeWorkIdentifier.objects.create(
            uri='http://share.osf.io/cats',
            creative_work=cw,
            creative_work_version=cw.versions.first(),
            change_id=change_ids.get())

        assert disambiguate('_:', {'creativeworkidentifiers': [identifier.pk]}, CreativeWork) == cw


class TestAffiliations:

    def test_handles_unique_violations(self):
        pass
