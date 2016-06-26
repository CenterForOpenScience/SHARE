import inspect

from django.db import models
from django.conf import settings
from django.db.models.base import ModelBase

from share.models.change import Change
from share.models import fields

from typedmodels import models as typedmodels


class ShareObjectVersion(models.Model):
    action = models.CharField(max_length=10)
    persistant_id = models.PositiveIntegerField()  # Must match the id of ShareObject

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
        'source': lambda: models.ForeignKey(settings.AUTH_USER_MODEL, null=True),
        'change': lambda: models.ForeignKey(Change, null=True, related_name='affected_%(class)s'),
        'date_modified': lambda: models.DateTimeField(auto_now=True),
        'date_created': lambda: models.DateTimeField(auto_now_add=True),
    }

    def __new__(cls, name, bases, attrs):
        if (models.Model in bases and attrs['Meta'].abstract) or len(bases) > 1:
            return super(ShareObjectMeta, cls).__new__(cls, name, bases, attrs)

        if hasattr(attrs.get('Meta'), 'db_table'):
            delattr(attrs['Meta'], 'db_table')

        # TODO Fix this in some None horrid fashion
        if name != 'ExtraData':
            attrs['extra'] = fields.ShareOneToOneField('ExtraData', null=True)

        version = super(ShareObjectMeta, cls).__new__(cls, name + 'Version', cls.version_bases, {
            **attrs,
            **{k: v() for k, v in cls.share_attrs.items()},
            '__qualname__': attrs['__qualname__'] + 'Version'
        })

        concrete = super(ShareObjectMeta, cls).__new__(cls, name, (bases[0], ) + cls.concrete_bases, {
            **attrs,
            **{k: v() for k, v in cls.share_attrs.items()},
            'VersionModel': version,
            'version': models.OneToOneField(version, editable=False, on_delete=models.PROTECT, related_name='%(app_label)s_%(class)s_version', null=True)
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


class VersionManager(models.Manager):

    def __init__(self, model=None, instance=None):
        super().__init__()
        self.model = model
        self.instance = instance

    def get_queryset(self):
        qs = self._queryset_class(model=self.model.VersionModel, using=self._db, hints=self._hints).order_by('-date_modified')
        if self.instance:
            return qs.filter(persistant_id=self.instance.id)
        return qs

    def contribute_to_class(self, model, name):
        super().contribute_to_class(model, name)
        if not model._meta.abstract:
            setattr(model, name, VersionManagerDescriptor(model))


class ExtraData(models.Model, metaclass=ShareObjectMeta):
    data = fields.DatetimeAwareJSONField(default={})

    objects = models.Manager()
    versions = VersionManager()

    class Meta:
        abstract = False


class ShareObject(models.Model, metaclass=ShareObjectMeta):
    id = models.AutoField(primary_key=True)
    objects = models.Manager()
    versions = VersionManager()

    class Meta:
        abstract = True
