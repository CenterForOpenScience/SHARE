import pytest

import jsonpatch

from share.models import Person
from share.models.core import ChangeStatus
from share.models.core import ChangeRequest


@pytest.mark.django_db
class TestChange:

    def test_apply_person(self, share_user):
        p = Person(given_name='John', family_name='Doe', source=share_user)
        change = ChangeRequest.objects.create_object(p, share_user)
        change.save()

        assert change.version == p.versions.first()
        assert ChangeStatus(change.status) == ChangeStatus.PENDING

        p = change.accept()

        assert ChangeStatus(change.status) == ChangeStatus.ACCEPTED

        p.given_name = 'Jane'
        request = ChangeRequest.objects.update_object(p, share_user)

        assert ChangeStatus(request.status) == ChangeStatus.PENDING

        request.save()
        request.accept()

        p.refresh_from_db()

        assert p.given_name == 'Jane'
        assert p.version != change.version
        assert ChangeStatus(request.status) == ChangeStatus.ACCEPTED
        assert p.versions.all()[1].given_name == 'John'

    def test_update_requires_saved(self, share_user):
        p = Person(given_name='John', family_name='Doe', source=share_user)

        with pytest.raises(AssertionError):
            ChangeRequest.objects.update_object(p, share_user)

    def test_create_requires_unsaved(self, share_user):
        change = ChangeRequest.objects.create_object(
            Person(given_name='John', family_name='Doe', source=share_user),
            share_user
        )
        change.save()
        p = change.accept()

        with pytest.raises(AssertionError):
            ChangeRequest.objects.create_object(p, share_user)

    def test_diffing(self, share_user):
        change = ChangeRequest.objects.create_object(
            Person(given_name='John', family_name='Doe', source=share_user),
            share_user
        )
        change.save()
        clean = change.accept()
        dirty = Person.objects.get(pk=clean.pk)

        dirty.given_name = 'Jane'
        dirty.family_name = 'Dough'

        patch = ChangeRequest.objects.make_patch(clean, dirty)

        assert isinstance(patch, jsonpatch.JsonPatch)
        assert len(patch.patch) == 2
        assert sorted(patch.patch, key=lambda x: x['path']) == [{
            'op': 'replace',
            'path': '/family_name',
            'value': 'Dough',
        }, {
            'op': 'replace',
            'path': '/given_name',
            'value': 'Jane',
        }]
