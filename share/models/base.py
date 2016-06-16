import inspect

from django.db import models
from django.db.models.base import ModelBase

from share.models.core import ShareSource
from share.models.change import ChangeRequest


class AbstractShareObject(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    source = models.ForeignKey(ShareSource)
    change = models.ForeignKey(ChangeRequest)
    # source_data = models.ForeignKey(RawData, blank=True, null=True)  # NULL/None indicates a user submitted change

    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class ShareObjectVersion(models.Model):
    action = models.CharField(max_length=10)
    persistant_id = models.PositiveIntegerField()  # Must match the id of ShareObject

    class Meta:
        abstract = True
        ordering = ('-date_modified', )


class ShareForeignKey(models.ForeignKey):

    def __init__(self, model, **kwargs):
        self.__kwargs = kwargs
        super().__init__(model, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        actual = self.__class__.mro()[1](self.remote_field.model, **self.__kwargs)
        actual.contribute_to_class(cls, name, **kwargs)

        self.__kwargs['editable'] = False
        version = self.__class__.mro()[1](self.remote_field.model.VersionModel, **self.__kwargs)
        version.contribute_to_class(cls, name + '_version', **kwargs)

        actual._share_version_field = version


class ShareManyToMany(models.ManyToManyField):

    def __init__(self, model, **kwargs):
        self.__kwargs = kwargs
        super().__init__(model, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        actual = self.__class__.mro()[1](self.remote_field.model, **self.__kwargs)
        actual.contribute_to_class(cls, name, **kwargs)

        self.__kwargs['through'] += 'Version'
        self.__kwargs['editable'] = False

        version = self.__class__.mro()[1](self.remote_field.model.VersionModel, **self.__kwargs)
        version.contribute_to_class(cls, name[:-1] + '_versions', **kwargs)

        actual._share_version_field = version


class ShareObjectMeta(ModelBase):

    def __new__(cls, name, bases, attrs):
        if models.Model in bases or len(bases) > 1:
            return super(ShareObjectMeta, cls).__new__(cls, name, bases, attrs)
        module = attrs['__module__']

        if not attrs.get('Meta'):
            attrs['Meta'] = type('Meta', (object, ), {})
        attrs['Meta'].abstract = True

        attrs['__qualname__'] = 'Abstract' + attrs['__qualname__']
        abstract = super(ShareObjectMeta, cls).__new__(cls, 'Abstract' + name, (AbstractShareObject, ), attrs)

        version = type(
            name + 'Version',
            (abstract, ShareObjectVersion),
            {'__module__': module}
        )

        concrete = super(ShareObjectMeta, cls).__new__(cls, name, (abstract, ShareObject), {
            '__module__': module,
            'VersionModel': version,
            'version': models.OneToOneField(version, editable=False, on_delete=models.PROTECT, related_name='%(app_label)s_%(class)s_version')
        })

        inspect.stack()[1].frame.f_globals.update({concrete.VersionModel.__name__: concrete.VersionModel})

        return concrete


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


class ShareObject(models.Model, metaclass=ShareObjectMeta):
    id = models.AutoField(primary_key=True)
    objects = models.Manager()
    versions = VersionManager()

    class Meta:
        abstract = True
