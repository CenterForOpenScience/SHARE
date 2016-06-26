import logging

from model_utils import Choices

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


__all__ = ('Change', 'ChangeSet', )
logger = logging.getLogger(__name__)


class ChangeSetManager(models.Manager):

    def from_graph(self, graph, submitter):
        cs = ChangeSet(submitted_by=submitter)
        cs.save()
        # cs.changes.add(*changes)
        return cs


class ChangeManager(models.Manager):

    def from_node(self, node, change_set, requirements=tuple()):
        attrs = {
            'change': node.change,
            'change_set': change_set,
            'target_type': ContentType.objects.get_for_model(node.model, for_concrete_model=False),
            'target_version_type': ContentType.objects.get_for_model(node.model.VersionModel, for_concrete_model=False),
        }

        if not node.model:
            attrs['type'] = Change.TYPE.merge
        elif not node.instance:
            attrs['type'] = Change.TYPE.create
        else:
            attrs['type'] = Change.TYPE.update
            attrs['target_id'] = node.instance.pk
            attrs['target_version_id'] = node.instance.version.pk

        return Change.objects.create(**attrs)


class ChangeSet(models.Model):
    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL)
#     # raw = models.ForeignKey(RawData, on_delete=models.PROTECT, null=True)
#     # normalization_log = models.ForeignKey(RawData, on_delete=models.PROTECT, null=True)


class Change(models.Model):
    TYPE = Choices((0, 'create', _('create')), (1, 'merge', _('merge')), (2, 'update', _('update')))
    STATUS = Choices((0, 'pending', _('pending')), (1, 'accepted', _('accepted')), (2, 'rejected', _('rejected')))

    objects = ChangeManager()
    # accepted = ChangeQuerySet

    change = JSONField()

    type = models.IntegerField(choices=TYPE)
    status = models.IntegerField(choices=STATUS, default=STATUS.pending)

    target_id = models.PositiveIntegerField(null=True)
    target = GenericForeignKey('target_type', 'target_id')
    target_type = models.ForeignKey(ContentType, related_name='target_%(class)s')

    target_version_type = models.ForeignKey(ContentType, related_name='target_version_%(class)s')
    target_version_id = models.PositiveIntegerField(null=True)
    target_version = GenericForeignKey('target_version_type', 'target_version_id')

    change_set = models.ForeignKey(ChangeSet, related_name='changes')
    requirements = models.ManyToManyField('Change', through='ChangeRequirement', related_name='something')

    def accept(self, save=True):
        if self.type == Change.TYPE.create:
            return self._create(save=save)
        if self.type == Change.TYPE.update:
            return self._update(save=save)

    def _create(self, save=True):
        inst = self.target_type.model_class()(change=self, **self.change)
        if save:
            inst.save()
        return inst

    def _update(self, save=True):
        self.target.change = self
        self.target.__dict__.update(self.change)
        if save:
            self.target.save()
        return self.target


class ChangeRequirement(models.Model):
    node_id = models.CharField(max_length=50)
    change = models.ForeignKey(Change, related_name='depends_on')
    requirement = models.ForeignKey(Change, related_name='required_by')
