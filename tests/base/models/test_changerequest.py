import pytest

import jsonpatch

from share.models import Email
from share.models import Person
from share.models import PersonEmail
from share.models.core import ChangeStatus
from share.models.core import ChangeRequest


@pytest.mark.django_db
class TestChange:

    def test_apply_person(self, share_source):
        p = Person(given_name='John', family_name='Doe', source=share_source)
        change = ChangeRequest.objects.create_object(p, share_source)
        change.save()

        assert change.version == p.versions.first()
        assert ChangeStatus(change.status) == ChangeStatus.PENDING

        p = change.accept()

        assert ChangeStatus(change.status) == ChangeStatus.ACCEPTED

        p.given_name = 'Jane'
        request = ChangeRequest.objects.update_object(p, share_source)

        assert ChangeStatus(request.status) == ChangeStatus.PENDING

        request.save()
        request.accept()

        p.refresh_from_db()

        assert p.given_name == 'Jane'
        assert p.version != change.version
        assert ChangeStatus(request.status) == ChangeStatus.ACCEPTED
        assert p.versions.all()[1].given_name == 'John'

    def test_update_requires_saved(self, share_source):
        p = Person(given_name='John', family_name='Doe', source=share_source)

        with pytest.raises(AssertionError):
            ChangeRequest.objects.update_object(p, share_source)

    def test_create_requires_unsaved(self, share_source):
        change = ChangeRequest.objects.create_object(
            Person(given_name='John', family_name='Doe', source=share_source),
            share_source
        )
        change.save()
        p = change.accept()

        with pytest.raises(AssertionError):
            ChangeRequest.objects.create_object(p, share_source)

    def test_diffing(self, share_source):
        change = ChangeRequest.objects.create_object(
            Person(given_name='John', family_name='Doe', source=share_source),
            share_source
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

    def test_requirements(self, share_source):
        p = Person(given_name='Jane', family_name='Doe', source=share_source)
        p_change = ChangeRequest.objects.create_object(p, share_source)

        e = Email(email='example@example.com', source=share_source)
        e_change = ChangeRequest.objects.create_object(e, share_source)

        pe = PersonEmail(email=e, person=p, source=share_source)

        change = ChangeRequest.objects.create_object(pe, share_source)

        assert change.depends_on.count() == 2

        expected = {
            'email_id': e_change,
            'person_id': p_change,
        }

        for req in change.depends_on.all():
            assert req.change == change
            assert req.requirement == expected[req.field]

    def test_requirements_must_be_accepted(self, share_source):
        p = Person(given_name='Jane', family_name='Doe', source=share_source)
        ChangeRequest.objects.create_object(p, share_source)

        e = Email(email='example@example.com', source=share_source)
        ChangeRequest.objects.create_object(e, share_source)

        pe = PersonEmail(email=e, person=p, source=share_source)

        change = ChangeRequest.objects.create_object(pe, share_source)

        with pytest.raises(AssertionError) as e:
            change.accept()

        assert e.value.args[0] == 'Not all dependancies have been accepted'

    def test_accept_requirements(self, share_source):
        p = Person(given_name='Jane', family_name='Doe', source=share_source)
        ChangeRequest.objects.create_object(p, share_source).accept()

        e = Email(email='example@example.com', is_primary=False, source=share_source)
        ChangeRequest.objects.create_object(e, share_source).accept()

        change = ChangeRequest.objects.create_object(
            PersonEmail(email=e, person=p, source=share_source),
            share_source
        )
        pe = change.accept()

        pe.refresh_from_db()

        assert pe.change == change
        assert pe.person.given_name == 'Jane'
        assert pe.person.family_name == 'Doe'
        assert pe.email.email == 'example@example.com'

    def test_mixed_requirements(self, share_source):
        p = ChangeRequest.objects.create_object(
            Person(given_name='Jane', family_name='Doe', source=share_source),
            share_source
        ).accept()

        e = Email(email='example@example.com', is_primary=False, source=share_source)
        e_change = ChangeRequest.objects.create_object(e, share_source)

        change = ChangeRequest.objects.create_object(
            PersonEmail(email=e, person=p, source=share_source),
            share_source
        )

        assert change.depends_on.count() == 1
        assert change.depends_on.first().requirement == e_change
