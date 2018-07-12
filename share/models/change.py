import logging

from model_utils import Choices

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import connection
from django.db import models
from django.db import transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from django.utils.translation import ugettext as _

from share.exceptions import IngestConflict
from share.models import NormalizedData
from share.models.fuzzycount import FuzzyCountManager
from share.models.indexes import ConcurrentIndex
from share.util import IDObfuscator, BaseJSONAPIMeta


__all__ = ('Change', 'ChangeSet', )
logger = logging.getLogger(__name__)


class ChangeSet(models.Model):
    STATUS = Choices((0, 'pending', _('pending')), (1, 'accepted', _('accepted')), (2, 'rejected', _('rejected')))

    objects = FuzzyCountManager()

    status = models.IntegerField(choices=STATUS, default=STATUS.pending)
    submitted_at = models.DateTimeField(auto_now_add=True)
    normalized_data = models.ForeignKey(NormalizedData, on_delete=models.CASCADE)

    _changes_cache = []

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    def accept(self, save=True):
        ret = []
        with transaction.atomic():
            self._changes_cache = list(self.changes.all())
            for c in self._changes_cache:
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

    objects = FuzzyCountManager()

    change = JSONField()
    node_id = models.TextField()

    type = models.IntegerField(choices=TYPE, editable=False)
    # The non-concrete type that this change has made
    model_type = models.ForeignKey(ContentType, related_name='+', db_index=False, on_delete=models.CASCADE)

    target_id = models.PositiveIntegerField(null=True)
    target = GenericForeignKey('target_type', 'target_id')
    target_type = models.ForeignKey(ContentType, related_name='target_%(class)s', on_delete=models.CASCADE)

    target_version_type = models.ForeignKey(ContentType, related_name='target_version_%(class)s', db_index=False, on_delete=models.CASCADE)
    target_version_id = models.PositiveIntegerField(null=True, db_index=False)
    target_version = GenericForeignKey('target_version_type', 'target_version_id')

    change_set = models.ForeignKey(ChangeSet, related_name='changes', on_delete=models.CASCADE)

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    class Meta:
        ordering = ('pk', )
        indexes = (
            ConcurrentIndex(fields=['target_id', 'target_type']),
        )

    def accept(self, save=True):
        # Little bit of blind faith here that all requirements have been accepted
        assert self.change_set.status == ChangeSet.STATUS.pending, 'Cannot accept a change with status {}'.format(self.change_set.status)
        logger.debug('Accepting change node ({}, {})'.format(ContentType.objects.get_for_id(self.model_type_id), self.node_id))
        try:
            ret = self._accept(save)
        except IntegrityError as e:
            if e.args[0].startswith('duplicate key value violates unique constraint'):
                raise IngestConflict
            raise

        if save:
            # Psuedo hack, sources.add(...) tries to do some safety checks.
            # Don't do that. We have a database. That is its job. Let it do its job.
            through_meta = ret._meta.get_field('sources').remote_field.through._meta

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
            self.target.recast(new_type)

        for k, v in self._resolve_change().items():
            setattr(self.target, k, v)

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
            field.model.objects.select_for_update().filter(**{
                field.name + '__in': change['from']
            }).update(**{
                'change': self,
                field.name: change['into'],
                field.name + '_version': change['into'].version,
                'date_modified': date_modified,
            })

        # Finally point all from rows' same_as and
        # same_as_version to the canonical model.
        type(change['into']).objects.select_for_update().filter(
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

        if self.target_type.model == 'subject':
            SubjectTaxonomy = apps.get_model('share', 'subjecttaxonomy')
            user = self.change_set.normalized_data.source
            central_synonym = change.get('central_synonym', self.target.central_synonym if self.target else None)
            if central_synonym is None and user.username != settings.APPLICATION_USERNAME:
                raise PermissionError('Only the system user can modify the central subject taxonomy, not {}'.format(user))
            change['taxonomy'], _ = SubjectTaxonomy.objects.get_or_create(source=user.source)

        return change
