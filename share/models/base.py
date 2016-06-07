import uuid
import inspect

from django.db import models
from django.conf import settings
from django.db import transaction
from django.db.models.base import ModelBase
from django.db.models.fields.related import lazy_related_operation

from share.models.core import RawData
from share.models.core import ShareUser


class AbstractShareObject(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    source = models.ForeignKey(ShareUser)
    source_data = models.ForeignKey(RawData, blank=True, null=True)  # NULL/None indicates a user submitted change

    changed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ShareObjectVersion(models.Model):
    action = models.CharField(max_length=10);
    persistant_id = models.PositiveIntegerField()  # Must match the id of ShareObject

    class Meta:
        abstract = True


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
            'version': models.OneToOneField(version, on_delete=models.PROTECT, related_name='%(app_label)s_%(class)s_version')
        })

        concrete.VersionModel = version

        inspect.stack()[1].frame.f_globals.update({concrete.VersionModel.__name__: concrete.VersionModel})

        return concrete


class ShareObject(models.Model, metaclass=ShareObjectMeta):
    id = models.AutoField(primary_key=True)

    class Meta:
        abstract = True
