import re
import copy
import inspect

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import DatabaseError
from django.db import models
from django.db import transaction
from django.db.models.base import ModelBase
from django.db.models.fields import AutoField
from django.utils.translation import ugettext_lazy as _

from typedmodels import models as typedmodels

from db.deletion import DATABASE_CASCADE

from share.models import fields
from share.models.change import Change
from share.models.fuzzycount import FuzzyCountManager
from share.models.sql import ShareObjectManager


class ShareObjectVersion(models.Model):
    action = models.TextField(max_length=10)
    objects = FuzzyCountManager()

    class Meta:
        abstract = True
        ordering = ('-date_modified', )


# Generates 2 class from the original definition of the model
# A concrete class, <classname>
# And a version class, <classname>Version
class ShareObjectMeta(ModelBase):
    concrete_bases = ()
    version_bases = (ShareObjectVersion, )

    # This if effectively the "ShareBaseClass"
    # Due to limitations in Django and TypedModels we cannot have an actual inheritance chain
    share_attrs = {
        'change': lambda: models.ForeignKey(Change, related_name='affected_%(class)s', editable=False, on_delete=DATABASE_CASCADE),
        'date_modified': lambda: models.DateTimeField(auto_now=True, editable=False, db_index=True, help_text=_('The date this record was modified by SHARE.')),
        'date_created': lambda: models.DateTimeField(auto_now_add=True, editable=False, help_text=_('The date of ingress to SHARE.')),
    }

    def __new__(cls, name, bases, attrs):
        if (models.Model in bases and attrs['Meta'].abstract) or len(bases) > 1:
            return super(ShareObjectMeta, cls).__new__(cls, name, bases, attrs)

        version_attrs = {}
        for key, val in attrs.items():
            if isinstance(val, models.Field) and (val.unique or val.db_index):
                val = copy.deepcopy(val)
                val._unique = False
                val.db_index = False
            if isinstance(val, models.Field) and val.is_relation:
                val = copy.deepcopy(val)
                if isinstance(val, models.ForeignKey) and not isinstance(val, fields.ShareForeignKey):
                    val.remote_field.related_name = '+'
                if isinstance(val, (fields.ShareForeignKey, fields.ShareManyToManyField, fields.ShareOneToOneField)):
                    val._kwargs = {**val._kwargs, 'related_name': '+', 'db_index': False}
            if key == 'Meta':
                val = type('VersionMeta', (val, ), {'unique_together': None, 'db_table': val.db_table + 'version' if hasattr(val, 'db_table') else None})
            version_attrs[key] = val

        # TODO Fix this in some non-horrid fashion
        if name != 'ExtraData':
            version_attrs['extra'] = fields.ShareForeignKey('ExtraData', null=True)

        version = super(ShareObjectMeta, cls).__new__(cls, name + 'Version', cls.version_bases, {
            **version_attrs,
            **cls.share_attrs,
            **{k: v() for k, v in cls.share_attrs.items()},  # Excluded sources from versions. They never get filled out
            'persistent_id': models.ForeignKey(name, db_column='persistent_id', related_name='+', on_delete=DATABASE_CASCADE),
            '__qualname__': attrs['__qualname__'] + 'Version',
            'same_as': fields.ShareForeignKey(name, null=True, related_name='+'),
        })

        if name != 'ExtraData':
            attrs['extra'] = fields.ShareOneToOneField('ExtraData', null=True)

        concrete = super(ShareObjectMeta, cls).__new__(cls, name, (bases[0], ) + cls.concrete_bases, {
            **attrs,
            **{k: v() for k, v in cls.share_attrs.items()},
            'VersionModel': version,
            'same_as': fields.ShareForeignKey(name, null=True, related_name='+'),
            'version': models.OneToOneField(version, editable=False, related_name='%(app_label)s_%(class)s_version', on_delete=DATABASE_CASCADE),
            # TypedManyToManyField works just like a normal field but has some special code to handle proxy models (if the exist)
            # and makes the database use ON DELETE CASCADE as opposed to Djangos software cascade
            'sources': fields.TypedManyToManyField(settings.AUTH_USER_MODEL, related_name='source_%(class)s', editable=False),
        })

        # Inject <classname>Version into the module of the original class definition
        next(frame for frame in inspect.stack() if 'class {}('.format(name) in frame.code_context[0]).frame.f_globals.update({concrete.VersionModel.__name__: concrete.VersionModel})

        return concrete


class TypedShareObjectMeta(ShareObjectMeta, typedmodels.TypedModelMetaclass):
    concrete_bases = (typedmodels.TypedModel,)
    version_bases = (ShareObjectVersion, typedmodels.TypedModel)

    def __new__(cls, name, bases, attrs):
        # Any subclasses of a class that already uses this metaclass will be
        # turned into a proxy to the original table via TypedModelMetaclass
        if ShareObject not in bases:
            version = typedmodels.TypedModelMetaclass.__new__(cls, name + 'Version', (bases[0].VersionModel, ), {
                **attrs,
                '__qualname__': attrs['__qualname__'] + 'Version'
            })

            # Our triggers don't update django typed's type field.
            # Makes the concrete type option resolve properly when loading versions from the db
            # And forces queries to use the concrete models key
            version._typedmodels_type = 'share.' + name.lower()
            version._typedmodels_registry['share.' + name.lower()] = version

            return typedmodels.TypedModelMetaclass.__new__(cls, name, bases, {**attrs, 'VersionModel': version})
        return super(TypedShareObjectMeta, cls).__new__(cls, name, bases, attrs)


class VersionManagerDescriptor:

    def __init__(self, model):
        self.model = model

    def __get__(self, instance, type=None):
        if instance is not None:
            return VersionManager(self.model, instance)
        return VersionManager(self.model, instance)


class VersionManager(FuzzyCountManager):

    def __init__(self, model=None, instance=None):
        super().__init__()
        self.model = model
        self.instance = instance

    def get_queryset(self):
        qs = self._queryset_class(model=self.model.VersionModel, using=self._db, hints=self._hints).order_by('-date_modified')
        if self.instance:
            return qs.filter(persistent_id=self.instance.id)
        return qs

    def contribute_to_class(self, model, name):
        super().contribute_to_class(model, name)
        if not model._meta.abstract:
            setattr(model, name, VersionManagerDescriptor(model))


class ExtraData(models.Model, metaclass=ShareObjectMeta):
    data = fields.DateTimeAwareJSONField(default=dict)

    objects = FuzzyCountManager()
    versions = VersionManager()

    class Meta:
        abstract = False


class ShareObject(models.Model, metaclass=ShareObjectMeta):
    id = models.AutoField(primary_key=True)
    objects = ShareObjectManager()
    versions = VersionManager()
    changes = fields.GenericRelationNoCascade('Change', related_query_name='share_objects', content_type_field='target_type', object_id_field='target_id', for_concrete_model=True)

    class Meta:
        abstract = True

    def administrative_change(self, **kwargs):
        from share.models import Change
        from share.models import ChangeSet
        from share.models import NormalizedData
        from share.models import ShareUser

        with transaction.atomic():
            assert kwargs, 'Don\'t make empty changes'

            nd = NormalizedData.objects.create(
                source=ShareUser.objects.get(username='system'),
                data={
                    '@graph': [{'@id': self.pk, '@type': self._meta.model_name, **kwargs}]
                }
            )

            cs = ChangeSet.objects.create(normalized_data=nd, status=ChangeSet.STATUS.accepted)
            change = Change.objects.create(change={}, node_id=str(self.pk), type=Change.TYPE.update, target=self, target_version=self.version, change_set=cs, model_type=ContentType.objects.get_for_model(type(self)))

            acceptable_fields = set(f.name for f in self._meta.get_fields())
            for key, value in kwargs.items():
                if key not in acceptable_fields:
                    raise AttributeError(key)
                setattr(self, key, value)
            self.change = change

            self.save()

    # NOTE/TODO Version will be popluated when a share object is first created
    # Updating a share object WILL NOT update the version
    def _save_table(self, raw=False, cls=None, force_insert=False, force_update=False, using=None, update_fields=None):
        """
        Does the heavy-lifting involved in saving. Updates or inserts the data
        for a single table.
        """
        meta = cls._meta
        non_pks = [f for f in meta.local_concrete_fields if not f.primary_key]

        if update_fields:
            non_pks = [f for f in non_pks
                       if f.name in update_fields or f.attname in update_fields]

        pk_val = self._get_pk_val(meta)
        if pk_val is None:
            pk_val = meta.pk.get_pk_value_on_save(self)
            setattr(self, meta.pk.attname, pk_val)
        pk_set = pk_val is not None
        if not pk_set and (force_update or update_fields):
            raise ValueError("Cannot force an update in save() with no primary key.")
        updated = False
        # If possible, try an UPDATE. If that doesn't update anything, do an INSERT.
        if pk_set and not force_insert:
            base_qs = cls._base_manager.using(using)
            values = [(f, None, (getattr(self, f.attname) if raw else f.pre_save(self, False)))
                      for f in non_pks]
            forced_update = update_fields or force_update
            updated = self._do_update(base_qs, using, pk_val, values, update_fields,
                                      forced_update)
            if force_update and not updated:
                raise DatabaseError("Forced update did not affect any rows.")
            if update_fields and not updated:
                raise DatabaseError("Save with update_fields did not affect any rows.")
        if not updated:
            if meta.order_with_respect_to:
                # If this is a model with an order_with_respect_to
                # autopopulate the _order field
                field = meta.order_with_respect_to
                filter_args = field.get_filter_kwargs_for_object(self)
                order_value = cls._base_manager.using(using).filter(**filter_args).count()
                self._order = order_value

            fields = meta.local_concrete_fields
            if not pk_set:
                fields = [f for f in fields if not isinstance(f, AutoField)]

            update_pk = bool(meta.has_auto_field and not pk_set)
            result = self._do_insert(cls._base_manager, using, fields, update_pk, raw)
            if update_pk:
                ### ACTUAL CHANGE HERE ###
                # Use regex as it will, hopefully, fail if something get messed up
                pk, version_id = re.match(r'\((\d+),(\d+)\)', result).groups()
                setattr(self, meta.pk.attname, int(pk))
                setattr(self, meta.get_field('version').attname, int(version_id))
                ### /ACTUAL CHANGE HERE ###
        return updated
