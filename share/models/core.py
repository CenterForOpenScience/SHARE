import enum
import logging
from hashlib import sha256

import jsonpatch

from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from share.models.util import ZipField

logger = logging.getLogger(__name__)
__all__ = ('ShareSource', 'RawData', 'ChangeRequest', 'ChangeStatus')


# class ShareTask(models.Model):
#     id = models.UUIDField()

#     args = models.CharField()
#     kwargs = models.JSONField()

#     task = models.CharField(max_length=64)
#     hostname = models.CharField(max_length=128)
#     status = models.IntField(default=0, choices=(
#         (0, 'Scheduled'),
#         (1, 'Accepted'),
#         (2, 'Started'),
#         (3, 'Succeeded'),
#     ))


class ShareSource(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=256)
    # Nullable as actual providers will not have users
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)

    @property
    def is_entity(self):
        return self.user is None

    @property
    def is_user(self):
        return self.user is not None


class RawDataManager(models.Manager):

    def store_data(self, doc_id, data, source):
        rd, created = self.get_or_create(
            source=source,
            doc_id=doc_id,
            sha256=sha256(data).hexdigest(),
            defaults={'data': data},
        )

        if created:
            logger.info('Newly created RawData for document {} from {}'.format(doc_id, source))
        else:
            logger.info('Saw exact copy of document {} from {}'.format(doc_id, source))

        rd.save()  # Force timestamps to update
        return rd


class RawData(models.Model):
    id = models.AutoField(primary_key=True)

    source = models.ForeignKey(ShareSource)
    provider_doc_id = models.CharField(max_length=256)

    data = ZipField(blank=False)
    sha256 = models.CharField(max_length=64)

    # date_processed = models.DateTimeField(null=True)

    date_seen = models.DateTimeField(auto_now=True)
    date_harvested = models.DateTimeField(auto_now_add=True)

    objects = RawDataManager()

    @property
    def processsed(self):
        return self.date_processed is not None

    class Meta:
        unique_together = (('provider_doc_id', 'source', 'sha256'),)


class ChangeStatus(enum.Enum):
    PENDING = 'P'
    ACCEPTED = 'A'
    REJECTED = 'R'


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
        assert obj.pk is None, 'Create object requires an unsaved object'
        changes = cls.make_patch(None, obj)

        return ChangeRequest(
            changes=changes.patch,
            submitted_by=submitter,
            status=ChangeStatus.PENDING.value,
            content_type=ContentType.objects.get_for_model(obj.__class__),
            version_content_type=ContentType.objects.get_for_model(obj.__class__.VersionModel),
        )

    @classmethod
    def update_object(cls, updated, submitter):
        assert updated.pk, 'Update objects requires a saved object'
        clean = updated.__class__.objects.get(pk=updated.pk)
        changes = cls.make_patch(clean, updated)

        return ChangeRequest(
            target=clean,
            version=clean.version,
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

    submitted_by = models.ForeignKey(ShareSource)
    submitted_at = models.DateTimeField(auto_now_add=True, editable=False)

    changes = JSONField()  # TODO Validator for jsonpatch or OTs

    raw = models.ForeignKey(RawData, on_delete=models.PROTECT, null=True)  # Null mean users submitted

    # All fields required for a generic foreign key
    # Points to any ShareObject
    object_id = models.PositiveIntegerField(null=True)
    target = GenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    # Points to any ShareObjectVersion
    version_id = models.PositiveIntegerField(null=True)
    version = GenericForeignKey('version_content_type', 'version_id')
    version_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,  related_name='%(app_label)s_%(class)s_version')

    objects = ChangeRequestManager()

    def reject(self):
        self.status = ChangeStatus.REJECTED.value

    def accept(self, force=False):
        assert force or self.status == ChangeStatus.PENDING.value
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
        self.version = inst.versions.first()
        return inst
