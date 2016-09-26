import copy
import inspect

import uuid

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.conf import settings
from django.db import transaction
from django.db.models.base import ModelBase
from fuzzycount import FuzzyCountManager

from share.models.change import Change
from share.models import fields

from typedmodels import models as typedmodels


class ShareObjectVersion(models.Model):
    action = models.TextField(max_length=10)
    persistent_id = models.PositiveIntegerField()  # Must match the id of ShareObject

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
        'sources': lambda: models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='source_%(class)s', editable=False),
        'change': lambda: models.OneToOneField(Change, related_name='affected_%(class)s', editable=False),
        'date_modified': lambda: models.DateTimeField(auto_now=True, editable=False, db_index=True),
        'date_created': lambda: models.DateTimeField(auto_now_add=True, editable=False),
        'uuid': lambda: models.UUIDField(default=uuid.uuid4, editable=False)
    }

    def __new__(cls, name, bases, attrs):
        if (models.Model in bases and attrs['Meta'].abstract) or len(bases) > 1:
            return super(ShareObjectMeta, cls).__new__(cls, name, bases, attrs)

        version_attrs = {}
        for key, val in attrs.items():
            if isinstance(val, models.Field) and val.unique:
                val = copy.deepcopy(val)
                val._unique = False
            if key == 'Meta':
                val = type('VersionMeta', (val, ), {'unique_together': None, 'db_table': None})
            version_attrs[key] = val

        # TODO Fix this in some non-horrid fashion
        if name != 'ExtraData':
            version_attrs['extra'] = fields.ShareForeignKey('ExtraData', null=True)

        version = super(ShareObjectMeta, cls).__new__(cls, name + 'Version', cls.version_bases, {
            **version_attrs,
            **{k: v() for k, v in cls.share_attrs.items()},
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
            'version': models.OneToOneField(version, editable=False, related_name='%(app_label)s_%(class)s_version'),
        })

        # Inject <classname>Version into the module of the original class definition
        # Makes shell_plus work
        inspect.stack()[1].frame.f_globals.update({concrete.VersionModel.__name__: concrete.VersionModel})

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
            return qs.filter(uuid=self.instance.uuid)
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
    objects = FuzzyCountManager()
    versions = VersionManager()
    changes = GenericRelation('Change', related_query_name='share_objects', content_type_field='target_type', object_id_field='target_id')

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
                normalized_data={
                    '@graph': [{'@id': self.pk, '@type': self._meta.model_name, **kwargs}]
                }
            )

            cs = ChangeSet.objects.create(normalized_data=nd, status=ChangeSet.STATUS.accepted)
            change = Change.objects.create(change={}, node_id=str(self.pk), type=Change.TYPE.update, target=self, target_version=self.version, change_set=cs)

            acceptable_fields = set(f.name for f in self._meta.get_fields())
            for key, value in kwargs.items():
                if key not in acceptable_fields:
                    raise AttributeError(key)
                setattr(self, key, value)
            self.change = change

            self.save()
