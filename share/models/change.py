import logging

from model_utils import Choices

from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import connection
from django.db import models
from django.db import transaction
from django.db import IntegrityError
from django.utils import timezone
from django.utils.translation import ugettext as _

from share.models.fuzzycount import FuzzyCountManager
from share.models import NormalizedData
from share.util import IDObfuscator


__all__ = ('Change', 'ChangeSet', )
logger = logging.getLogger(__name__)


class ChangeSetManager(FuzzyCountManager):

    def from_graph(self, graph, normalized_data_id):
        if all(n.is_skippable for n in graph.nodes):
            logger.debug('No changes detected in {!r}, skipping.'.format(graph))
            return None

        cs = ChangeSet(normalized_data_id=normalized_data_id)
        cs.save()

        Change.objects.bulk_create(filter(None, [Change.objects.from_node(node, cs, save=False) for node in graph.nodes]))

        return cs


class ChangeManager(FuzzyCountManager):

    def from_node(self, node, change_set, save=True):
        if node.is_skippable:
            logger.debug('No changes detected in {!r}, skipping.'.format(node))
            return None
        if not hasattr(node.model, 'VersionModel'):
            # Non-ShareObjects (e.g. Subject) cannot be changed.
            # Shouldn't reach this point...
            logger.warn('Change node {!r} targets immutable model {}, skipping.'.format(node, node.model))
            return None

        attrs = {
            'node_id': node.id,
            'change': node.change,
            'change_set': change_set,
            'model_type': ContentType.objects.get_for_model(node.model, for_concrete_model=False),
            'target_type': ContentType.objects.get_for_model(node.model, for_concrete_model=True),
            'target_version_type': ContentType.objects.get_for_model(node.model.VersionModel, for_concrete_model=True),
        }

        if not node.instance:
            assert not node.is_merge
            attrs['type'] = Change.TYPE.create
        else:
            attrs['type'] = Change.TYPE.merge if node.is_merge else Change.TYPE.update
            attrs['target_id'] = node.instance.pk
            attrs['target_version_id'] = node.instance.version.pk

        change = Change(**attrs)

        if save:
            change.save()

        return change


class ChangeSet(models.Model):
    STATUS = Choices((0, 'pending', _('pending')), (1, 'accepted', _('accepted')), (2, 'rejected', _('rejected')))

    objects = ChangeSetManager()

    status = models.IntegerField(choices=STATUS, default=STATUS.pending)
    submitted_at = models.DateTimeField(auto_now_add=True)
    normalized_data = models.ForeignKey(NormalizedData)

    _changes_cache = []

    def accept(self, save=True):
        ret = []
        with transaction.atomic():
            self._changes_cache = list(self.changes.all())
            for c in sorted(self._changes_cache, key=lambda c: c.type):
                ret.append(c.accept(save=save))
            self.status = ChangeSet.STATUS.accepted
            if save:
                self.save()
        return ret

    def _resolve_ref(self, ref):
        model = apps.get_model('share', model_name=ref['@type'])
        ct = ContentType.objects.get_for_model(model, for_concrete_model=True)
        try:
            if ref['@id'].startswith('_:'):
                return next(
                    change.target
                    for change in self._changes_cache
                    if change.target_type == ct
                    and change.node_id == ref['@id']
                    and change.target
                )
            return model._meta.concrete_model.objects.get(pk=IDObfuscator.decode_id(ref['@id']))
        except (StopIteration, model.DoesNotExist) as ex:
            raise Exception('Could not resolve reference {}'.format(ref)) from ex

    def __repr__(self):
        return '<{}({}, {}, {} changes)>'.format(self.__class__.__name__, self.STATUS[self.status].upper(), self.normalized_data.source, self.changes.count())


class Change(models.Model):
    TYPE = Choices((0, 'create', _('create')), (1, 'merge', _('merge')), (2, 'update', _('update')))

    objects = ChangeManager()

    change = JSONField()
    node_id = models.TextField()

    type = models.IntegerField(choices=TYPE, editable=False)
    # The non-concrete type that this change has made
    model_type = models.ForeignKey(ContentType, related_name='+', db_index=False)

    target_id = models.PositiveIntegerField(null=True)
    target = GenericForeignKey('target_type', 'target_id')
    target_type = models.ForeignKey(ContentType, related_name='target_%(class)s')

    target_version_type = models.ForeignKey(ContentType, related_name='target_version_%(class)s', db_index=False)
    target_version_id = models.PositiveIntegerField(null=True, db_index=False)
    target_version = GenericForeignKey('target_version_type', 'target_version_id')

    change_set = models.ForeignKey(ChangeSet, related_name='changes')

    class Meta:
        ordering = ('pk', )

    def accept(self, save=True):
        # Little bit of blind faith here that all requirements have been accepted
        assert self.change_set.status == ChangeSet.STATUS.pending, 'Cannot accept a change with status {}'.format(self.change_set.status)
        logger.debug('Accepting change node ({}, {})'.format(ContentType.objects.get_for_id(self.model_type_id), self.node_id))
        ret = self._accept(save)

        if save:
            # Psuedo hack, sources.add(...) tries to do some safety checks.
            # Don't do that. We have a database. That is its job. Let it do its job.
            through_meta = ret._meta.get_field('sources').rel.through._meta

            with connection.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO "{0}"
                        ("{1}", "{2}")
                    VALUES
                        (%s, %s)
                    ON CONFLICT DO NOTHING;
                '''.format(
                    through_meta.db_table,
                    through_meta.get_field(ret._meta.concrete_model._meta.model_name).column,
                    through_meta.get_field('shareuser').column,
                ), (ret.pk, self.change_set.normalized_data.source_id))

            self.save()
        else:
            logger.warning('Calling accept with save=False will not update the sources field')

        return ret

    def _accept(self, save):
        if self.type == Change.TYPE.create:
            return self._create(save=save)
        if self.type == Change.TYPE.update:
            return self._update(save=save)
        return self._merge(save=save)

    def _create(self, save=True):
        resolved_change = self._resolve_change()
        inst = ContentType.objects.get_for_id(self.model_type_id).model_class()(change=self, **resolved_change)
        if save:
            inst.save()
        self.target = inst
        return inst

    def _update(self, save=True):
        self.target.change = self

        new_type = self.change.pop('@type', None)
        if new_type:
            self.target.recast('share.{}'.format(new_type))

        self.target.__dict__.update(self._resolve_change())
        if save:
            self.target.save()
        return self.target

    def _merge(self, save=True):
        from share.models.base import ShareObject
        assert save is True, 'Cannot perform merge without saving'

        # For now, don't let merge nodes also update fields
        assert len(self.change) == 1 and 'same_as' in self.change

        change = self._resolve_change()
        same_as = change['same_as']
        assert same_as._meta.concrete_model is self.target._meta.concrete_model

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

        for field in fields:
            # Update all foreign keys to point to same_as
            for obj in field.model.objects.filter(**{field.name: self.target_id}):
                try:
                    obj.change = self
                    setattr(obj, field.name, same_as)
                    with transaction.atomic():
                        obj.save()
                except IntegrityError as e:
                    # TODO handle this... merge fields on conflicting relations? set obj.same_as? delete obj?
                    logger.warn('Conflict updating %s.%s while merging %s into %s', field.model._meta.model_name, field.name, self.target, same_as)

        # Avoid same_as chains
        for obj in self.target_type._meta.concrete_model.objects.filter(same_as=self.target_id):
            obj.change = self
            obj.same_as = same_as
            obj.same_as_version = same_as.version
            obj.save()

        self.target.change = self
        self.target.same_as = same_as
        self.target.same_as_version = same_as.version
        self.target.save()

        # TODO [SHARE-539] merge scalar fields into same_as

        return same_as

    def _resolve_change(self):
        change = {}
        for k, v in self.change.items():
            if k == 'extra':
                if not v:
                    continue
                if self.target and self.target.extra:
                    change[k] = self.target.extra
                else:
                    from share.models.base import ExtraData
                    change[k] = ExtraData()
                change[k].change = self
                change[k].data.update({self.change_set.normalized_data.source.username: v})
                change[k].save()
                change[k + '_version_id'] = change[k].version_id
            elif isinstance(v, dict):
                inst = self.change_set._resolve_ref(v)
                change[k] = inst
                try:
                    change[k + '_version_id'] = inst.version_id
                except AttributeError:
                    # this isn't a ShareObject, no worries
                    pass
            elif isinstance(v, list):
                change[k] = [self.change_set._resolve_ref(r) for r in v]
            else:
                change[k] = v
        return change
