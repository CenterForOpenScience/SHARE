import enum

import jsonpatch

from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from share.models.util import ZipField

__all__ = ('ShareUser', 'RawData', 'ChangeRequest', 'ChangeStatus')


class ShareUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # short_id = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=50, null=True)
    is_entity = models.BooleanField(default=False)


class RawData(models.Model):
    id = models.AutoField(primary_key=True)
    data = ZipField(blank=False)
    source = models.ForeignKey(ShareUser)


class ChangeStatus(enum.Enum):
    PENDING = 'P'
    ACCEPTED = 'A'
    REJECTED = 'R'


class ChangeManager(models.Manager):

    @classmethod
    def make_patch(cls, clean, dirty):
        return jsonpatch.make_patch({
            field.column: field.value_from_object(clean)
            for field in clean and clean._meta.fields or []
            if field.editable
        }, {
            field.column: field.value_from_object(dirty)
            for field in dirty._meta.fields
            if field.editable
        })

    @classmethod
    def create_object(cls, obj, submitter):
        assert obj.pk is None, 'Create object requires an unsaved object'
        changes = cls.make_patch(None, obj)

        return ChangeRequest(
            changes=changes.patch,
            submitted_by=submitter,
            status=ChangeStatus.PENDING.value,
            content_type=ContentType.objects.get_for_model(obj.__class__)
        )

    @classmethod
    def update_object(cls, updated, submitter):
        assert updated.pk, 'Update objects requires a saved object'
        clean = updated.__class__.objects.get(pk=updated.pk)
        changes = cls.make_patch(clean, updated)

        return ChangeRequest(
            target=clean,
            changes=changes.patch,
            submitted_by=submitter,
            status=ChangeStatus.PENDING.value,
        )


class ChangeRequest(models.Model):
    id = models.AutoField(primary_key=True)

    status = models.CharField(
        max_length=1,
        choices=tuple((opt.name.capitalize(), opt.value) for opt in ChangeStatus.__members__.values()),
        default=ChangeStatus.PENDING.value
    )

    submitted_by = models.ForeignKey(ShareUser)
    submitted_at = models.DateTimeField(auto_now_add=True, editable=False)

    changes = JSONField()  # TODO Validator for jsonpatch or OTs

    # All fields required for a generic foreign key
    # Points to any ShareObject
    object_id = models.PositiveIntegerField(null=True)
    target = GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    objects = ChangeManager()

    def rejected(self):
        self.status = ChangeStatus.REJECTED.value

    def accept(self):
        self.status = ChangeStatus.ACCEPTED.value
        if self.target:
            return self.apply_change()
        return self.create_object()

    def apply_change(self):
        jsonpatch.apply_patch(self.target.__dict__, self.changes, in_place=True)
        self.target.save()
        return self.target

    def create_object(self):
        inst = self.content_type.model_class()()
        jsonpatch.apply_patch(inst.__dict__, self.changes, in_place=True)
        inst.change = self
        inst.save()
        self.target = inst
        return inst
