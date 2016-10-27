import pytest

from share.models import WorkIdentifier, CreativeWork
from share.disambiguation import AbstractCreativeWorkDisambiguator


class TestAbstractWork:

    @pytest.mark.django_db
    def test_does_not_disambiguate_without_identifier(self, change_ids):
        CreativeWork.objects.create(
            title='all about giraffes',
            description='see here is the the thing about giraffes',
            change_id=change_ids.get()
        )
        disWork = AbstractCreativeWorkDisambiguator('_:', {'title': 'all about giraffes'}, CreativeWork).find()

        assert disWork is None

    @pytest.mark.django_db
    def test_disambiguate_by_identifier(self, change_ids):
        cw = CreativeWork.objects.create(
            title='All about cats',
            description='see here is the the thing about emptiness',
            change_id=change_ids.get()
        )

        identifier = WorkIdentifier.objects.create(
            uri='http://share.osf.io/cats',
            creative_work=cw,
            creative_work_version=cw.versions.first(),
            change_id=change_ids.get())

        disWork = AbstractCreativeWorkDisambiguator('_:', {'identifiers': [identifier.pk]}, CreativeWork).find()

        assert disWork == cw

    @pytest.mark.django_db
    def test_disambiguate_to_multiple(self, change_ids):
        uri1 = 'http://share.osf.io/cats',
        uri2 = 'http://osf.io/cats',

        cw1 = CreativeWork.objects.create(
            title='All about cats',
            description='see here is the the thing about emptiness',
            change_id=change_ids.get()
        )
        identifier1 = WorkIdentifier.objects.create(
            uri=uri1,
            creative_work=cw1,
            creative_work_version=cw1.versions.first(),
            change_id=change_ids.get())

        cw2 = CreativeWork.objects.create(
            title='All about cats',
            description='see here is the the thing about emptiness',
            change_id=change_ids.get()
        )
        identifier2 = WorkIdentifier.objects.create(
            uri=uri2,
            creative_work=cw2,
            creative_work_version=cw2.versions.first(),
            change_id=change_ids.get())

        disWorks = AbstractCreativeWorkDisambiguator('_:', {'identifiers': [identifier1.pk, identifier2.pk]}, CreativeWork).find()

        assert isinstance(disWorks, list)
        assert disWorks[0] == cw1
        assert disWorks[1] == cw2


class TestAffiliations:

    def test_handles_unique_violations(self):
        pass
