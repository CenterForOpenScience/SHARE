import copy
import logging

import jsonpatch

from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from enumfields import Enum
from enumfields import EnumField

from share.models.core import ShareSource


__all__ = ('ChangeRequest', )
logger = logging.getLogger(__name__)


class ChangeRequirementManager(models.Manager):

    def from_field(self, obj, field):
        return ChangeRequirement(
            change=obj.change,
            field=field.column,
            version_field=field._share_version_field.column,
            requirement=getattr(obj, field.name).change,
        )


class ChangeRequestManager(models.Manager):

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
        from share.models.base import ShareObject  # Circular import
        assert obj.pk is None, 'Create object requires an unsaved object'
        changes = cls.make_patch(None, obj)

        change = ChangeRequest(
            changes=changes.patch,
            submitted_by=submitter,
            status=ChangeRequest.Status.PENDING,
            content_type=ContentType.objects.get_for_model(obj.__class__),
            version_content_type=ContentType.objects.get_for_model(obj.__class__.VersionModel),
        )

        change.save()
        obj.change = change

        for field in obj._meta.fields:
            if field.editable and field.is_relation and issubclass(field.related_model, ShareObject) and getattr(obj, field.name) and getattr(obj, field.name).pk is None:
                ChangeRequirement.objects.from_field(obj, field).save()

        return change

    @classmethod
    def update_object(cls, updated, submitter):
        assert updated.pk, 'Update objects requires a saved object'
        clean = updated.__class__.objects.get(pk=updated.pk)
        changes = cls.make_patch(clean, updated)

        ret = ChangeRequest(
            target=clean,
            version=clean.version,
            changes=changes.patch,
            submitted_by=submitter,
            status=ChangeRequest.Status.PENDING,
        )
        ret.save()
        return ret


class Status(Enum):
    PENDING = 'P'
    ACCEPTED = 'A'
    REJECTED = 'R'


class ChangeRequest(models.Model):
    Status = Status

    id = models.AutoField(primary_key=True)

    status = EnumField(Status, max_length=1, default=Status.PENDING)

    requires = models.ManyToManyField('ChangeRequest', through='ChangeRequirement')

    submitted_by = models.ForeignKey(ShareSource)
    submitted_at = models.DateTimeField(auto_now_add=True, editable=False)

    changes = JSONField()  # TODO Validator for jsonpatch or OTs

    # Null mean users submitted
    # raw = models.ForeignKey(RawData, on_delete=models.PROTECT, null=True)
    # normalization_log = models.ForeignKey(RawData, on_delete=models.PROTECT, null=True)

    # All fields required for a generic foreign key
    # Points to any ShareObject
    object_id = models.PositiveIntegerField(null=True)
    target = GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)

    # Points to any ShareObjectVersion
    version_id = models.PositiveIntegerField(null=True)
    version = GenericForeignKey('version_content_type', 'version_id')
    version_content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT,  related_name='%(app_label)s_%(class)s_version')

    objects = ChangeRequestManager()

    def reject(self):
        self.status = ChangeRequest.Status.REJECTED
        self.save()

    def accept(self, force=False, recurse=False):
        if recurse:
            for request in self.depends_on.select_related('requirement').filter(requirement__status=ChangeRequest.Status.PENDING):
                request.requirement.accept(recurse=recurse)

        assert force or self.status == ChangeRequest.Status.PENDING
        assert self.depends_on.exclude(requirement__status=ChangeRequest.Status.ACCEPTED).count() == 0, 'Not all dependancies have been accepted'

        self.status = ChangeRequest.Status.ACCEPTED

        if self.target:
            return self.apply_change()
        return self.create_object()

    def apply_change(self):
        jsonpatch.apply_patch(self.target.__dict__, self.changes, in_place=True)
        self.target.source == self.submitted_by
        self.target.save()
        self.save()
        return self.target

    def create_object(self):
        inst = self.content_type.model_class()()
        for req in self.depends_on.all():  # TODO Avoid N+1 selects
            next(c for c in self.changes if c['path'] == '/' + req.field)['value'] = req.requirement.object_id
            self.changes.append({
                'op': 'replace',
                'path': '/' + req.version_field,
                'value': req.requirement.version_id
            })

        jsonpatch.apply_patch(inst.__dict__, self.changes, in_place=True)
        inst.change = self
        inst.source = self.submitted_by
        inst.save()
        self.target = inst
        self.version = inst.versions.first()
        self.save()
        return inst


class ChangeRequirement(models.Model):
    objects = ChangeRequirementManager()

    field = models.CharField(max_length=128)
    version_field = models.CharField(max_length=128)
    change = models.ForeignKey(ChangeRequest, related_name='depends_on')
    requirement = models.ForeignKey(ChangeRequest, related_name='required_by')
