import logging

from model_utils import Choices

from django.db import models
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from fuzzycount import FuzzyCountManager

__all__ = ('Change', 'ChangeSet', )
logger = logging.getLogger(__name__)


class ChangeSetManager(FuzzyCountManager):

    def from_graph(self, graph, submitter):
        if all(not n.change for n in graph.nodes):
            logger.info('No changes detected in {!r}, skipping.'.format(graph))
            return None

        cs = ChangeSet(submitted_by=submitter)
        cs.save()

        for node in graph.nodes:
            Change.objects.from_node(node, cs)

        return cs


class ChangeManager(FuzzyCountManager):

    def from_node(self, node, change_set):
        if not node.change:
            logger.info('No changes detected in {!r}, skipping.'.format(node))
            return None

        attrs = {
            'node_id': str(node.id),
            'change': node.change,
            'change_set': change_set,
            'target_type': ContentType.objects.get_for_model(node.model, for_concrete_model=False),
            'target_version_type': ContentType.objects.get_for_model(node.model.VersionModel, for_concrete_model=False),
        }

        if node.is_merge:
            attrs['type'] = Change.TYPE.merge
        elif not node.instance:
            attrs['type'] = Change.TYPE.create
        else:
            attrs['type'] = Change.TYPE.update
            attrs['target_id'] = node.instance.pk
            attrs['target_version_id'] = node.instance.version.pk

        change = Change.objects.create(**attrs)

        return change


class ChangeSet(models.Model):
    STATUS = Choices((0, 'pending', _('pending')), (1, 'accepted', _('accepted')), (2, 'rejected', _('rejected')))

    objects = ChangeSetManager()

    status = models.IntegerField(choices=STATUS, default=STATUS.pending)
    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL)
#     # raw = models.ForeignKey(RawData, on_delete=models.PROTECT, null=True)
#     normalization_log = models.ForeignKey(RawData, on_delete=models.PROTECT, null=True)

    def accept(self, save=True):
        with transaction.atomic():
            ret = [c.accept(save=save) for c in self.changes.all()]
            self.status = ChangeSet.STATUS.accepted
            if save:
                self.save()
        return ret

    def __repr__(self):
        return '<{}({}, {}, {} changes)>'.format(self.__class__.__name__, self.STATUS[self.status].upper(), self.submitted_by, self.changes.count())


class Change(models.Model):
    TYPE = Choices((0, 'create', _('create')), (1, 'merge', _('merge')), (2, 'update', _('update')))

    objects = ChangeManager()

    change = JSONField()
    node_id = models.CharField(max_length=80)  # TODO

    type = models.IntegerField(choices=TYPE, editable=False)

    target_id = models.PositiveIntegerField(null=True)
    target = GenericForeignKey('target_type', 'target_id')
    target_type = models.ForeignKey(ContentType, related_name='target_%(class)s')

    target_version_type = models.ForeignKey(ContentType, related_name='target_version_%(class)s')
    target_version_id = models.PositiveIntegerField(null=True)
    target_version = GenericForeignKey('target_version_type', 'target_version_id')

    change_set = models.ForeignKey(ChangeSet, related_name='changes')

    class Meta:
        ordering = ('pk', )

    def get_requirements(self):
        node_ids, content_types = [], set()
        for x in self.change.values():
            if isinstance(x, dict):
                node_ids.append(x['@id'])
                content_types.add(ContentType.objects.get(app_label='share', model=x['@type']))

        return Change.objects.filter(
            node_id__in=node_ids,
            change_set=self.change_set,
            target_type__in=content_types,
        )

    def accept(self, save=True):
        # Little bit of blind faith here that all requirements have been accepted
        assert self.change_set.status == ChangeSet.STATUS.pending, 'Cannot accept a change with status {}'.format(self.status)
        ret = self._accept(save)
        if save:
            self.save()
        return ret

    def _accept(self, save):
        if self.type == Change.TYPE.create:
            return self._create(save=save)
        if self.type == Change.TYPE.update:
            return self._update(save=save)
        return self._merge(save=save)

    def _create(self, save=True):
        inst = self.target_type.model_class()(change=self, **self._resolve_change())
        if save:
            inst.save()
        return inst

    def _update(self, save=True):
        self.target.change = self
        self.target.__dict__.update(self.change)
        if save:
            self.target.save()
        return self.target

    def _merge(self, save=True):
        from share.models.base import ShareObject
        assert save is True, 'Cannot perform merge without saving'

        change = self._resolve_change()
        # Find all fields that reference this model
        fields = [
            field.field for field in
            self.target_type.model_class()._meta.get_fields()
            if field.is_relation
            and not field.many_to_many
            and field.remote_field
            and issubclass(field.remote_field.model, ShareObject)
            and hasattr(field, 'field')
        ]

        # NOTE: Date is pinned up here to ensure its the same for all changed rows
        date_modified = timezone.now()

        for field in fields:
            # Update all rows in "from"
            # Updates the change, the field in question, the version pin of the field in question
            # and date_modified must be manually updated
            field.model.objects.filter(**{
                field.name + '__in': change['from']
            }).update(**{
                'change': self,
                field.name: change['into'],
                field.name + '_version': change['into'].version,
                'date_modified': date_modified,
            })

        # Finally point all from rows' same_as and
        # same_as_version to the canonical model.
        type(change['into']).objects.filter(
            pk__in=[i.pk for i in change['from']]
        ).update(
            change=self,
            same_as=change['into'],
            same_as_version=change['into'].version,
            date_modified=date_modified,
        )

        return change['into']

    def _resolve_change(self):
        change = {}
        for k, v in self.change.items():
            if isinstance(v, dict):
                inst = self._resolve_ref(v)
                change[k] = inst
                change[k + '_version'] = inst.version
            elif isinstance(v, list):
                change[k] = [self._resolve_ref(r) for r in v]
            else:
                change[k] = v
        extra = change.pop('extra', None)
        if extra:
            change['extra'] = {self.change_set.submitted_by.username: extra}
        return change

    def _resolve_ref(self, ref):
        ct = ContentType.objects.get(app_label='share', model=ref['@type'])
        if str(ref['@id']).startswith('_:'):
            return ct.model_class().objects.get(
                change__target_type=ct,
                change__node_id=ref['@id'],
                change__change_set=self.change_set,
            )
        return ct.model_class().objects.get(pk=ref['@id'])
