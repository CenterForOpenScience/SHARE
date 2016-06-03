import inspect

from django.db import models
from django.db.models.base import ModelBase
from django.contrib.auth.models import User


class ShareVersion:
    id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(User)
    created_at = models.DateTimeField()#(auto_add_now=True)
    persistant_id = models.CharField(max_length=256)

    class Meta:
        abstract = True


class ShareCurrent:
    id = models.CharField(max_length=256, primary_key=True)  # Persistant ID


class ShareAbstract:
    pass


class ShareRelation:

    @property
    def django(self):
        return self.django_class(self.model, **self.kwargs)

    @property
    def version(self):
        if not issubclass(self.model, ShareModel):
            return self.django
        return self.django_class(self.model.Version, **self.kwargs)

    @property
    def current(self):
        if not issubclass(self.model, ShareModel):
            return self.django
        return self.django_class(self.model.Current, **self.kwargs)

    def __init__(self, model, **kwargs):
        self.model = model
        self.kwargs = kwargs


class ShareManyToManyField(ShareRelation):
    django_class = models.ManyToManyField


class ShareForeignKey(ShareRelation):
    django_class = models.ForeignKey


class ShareMeta(ModelBase):

    def __new__(cls, name, bases, attrs):
        if models.Model in bases or len(bases) > 1:
            return super(ShareMeta, cls).__new__(cls, name, bases, attrs)

        module = attrs['__module__']

        if not attrs.get('Meta'):
            attrs['Meta'] = type('Meta', (object, ), {})
        attrs['Meta'].abstract = True

        for k, v in tuple(attrs.items()):
            if not isinstance(v, ShareRelation):
                continue
            attrs[k] = v.current

        class ConcreteMeta(attrs['Meta']):
            managed = False

        class Meta(attrs['Meta']):
            managed = True

        attrs['__qualname__'] = 'Abstract' + attrs['__qualname__']
        abstract = super(ShareMeta, cls).__new__(cls, 'Abstract' + name, bases, attrs)
        concrete = type(name, (abstract, ShareAbstract), {'__module__': module})

        concrete.Abstract = abstract

        concrete.Version = type(
            name + 'Version',
            (abstract, ShareVersion),
            {
                'Meta': Meta,
                '__module__': module,
            }
        )

        concrete.Current = type(
            name + 'Current',
            (abstract, ShareCurrent),
            {
                'Meta': Meta,
                '__module__': module,
                'version': models.ForeignKey(concrete.Version),
            }
        )

        inspect.stack()[1].frame.f_globals.update({
            concrete.Abstract.__name__: concrete.Abstract,
            concrete.Version.__name__: concrete.Version,
            concrete.Current.__name__: concrete.Current,
        })

        return concrete

class ShareModel(models.Model, metaclass=ShareMeta):

    class Meta:
        abstract = True
