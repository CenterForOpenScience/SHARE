import pytest

from share.models import Link
from share.models import CreativeWork
from share.models.meta import ThroughLinks
from share.disambiguation import disambiguate


class TestAbstractWork:

    @pytest.mark.django_db
    def test_disambiguates(self, change_ids):
        oldWork = CreativeWork.objects.create(
            title='all about giraffes',
            description='see here is the the thing about giraffes',
            change_id=change_ids.get()
        )
        disWork = disambiguate('_:', {'title': 'all about giraffes'}, CreativeWork)

        assert disWork is not None
        assert disWork.id == oldWork.id
        assert disWork.title == oldWork.title
        assert disWork.description == oldWork.description

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
    def test_links_disambiguate(self, change_ids):
        cw = CreativeWork.objects.create(
            title='All about cats',
            description='see here is the the thing about emptiness',
            change_id=change_ids.get()
        )

        link = Link.objects.create(url='http://share.osf.io/cats', type='provider', change_id=change_ids.get())

        ThroughLinks.objects.create(
            link=link,
            creative_work=cw,
            change_id=change_ids.get(),
            link_version=link.versions.first(),
            creative_work_version=cw.versions.first(),
        )

        assert disambiguate('_:', {'links': [link.pk]}, CreativeWork) == cw


class TestAffiliations:

    def test_handles_unique_violations(self):
        pass
