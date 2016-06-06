import uuid
import inspect

from django.db import models
from django.conf import settings
from django.db import transaction
from django.db.models.base import ModelBase

from share.models.core import RawData


class ShareRelation:

    DJANGO_FIELD = None

    def __init__(self, related):
        assert issubclass(related, ShareModel), 'ShareRelations may only be used with ShareModels. Got {!r}'.format(related)
        self.related = related

    def for_version(self, **kwargs):
        return self.DJANGO_FIELD(self.related.Current, **kwargs)

    def for_concrete(self, **kwargs):
        return self.DJANGO_FIELD(self.related, **kwargs)

    def for_current(self, **kwargs):
        return None


class ShareForeignKey(ShareRelation):
    DJANGO_FIELD = models.ForeignKey


class ShareManyToMany(ShareRelation):

    DJANGO_FIELD = models.ManyToManyField

    def __init__(self, related, through):
        self.through = through
        super().__init__(related)

    def for_version(self, **kwargs):
        return None
        # import ipdb; ipdb.set_trace()
        # return super().for_version(**{**kwargs, 'through': self.through + 'Version'})

    def for_concrete(self, **kwargs):
        return super().for_concrete(**{**kwargs, 'through': self.through})

    def for_current(self, **kwargs):
        return self.DJANGO_FIELD(self.related.Current, **{**kwargs, 'through': self.through + 'Version'})


class ShareAbstract:
    pass


class ShareVersion(models.Model):
    id = models.AutoField(primary_key=True)
    source_data = models.ForeignKey(RawData, blank=True, null=True)  # NULL/None indicates a user submitted change
    source = models.ForeignKey(settings.AUTH_USER_MODEL)
    created_at = models.DateTimeField(auto_now=True)
    persistant_id = models.UUIDField()  # TODO Maybe make this a foreign Key

    class Meta:
        abstract = True


class ShareCurrent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class ShareConcrete(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_data = models.ForeignKey(RawData, blank=True, null=True)  # NULL/None indicates a user submitted change
    source = models.ForeignKey(settings.AUTH_USER_MODEL)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ShareMeta(ModelBase):

    def __new__(cls, name, bases, attrs):
        if models.Model in bases or len(bases) > 1:
            return super(ShareMeta, cls).__new__(cls, name, bases, attrs)

        module = attrs['__module__']

        relations = {}
        for k, v in tuple(attrs.items()):
            if isinstance(v, ShareRelation):
                relations[k] = attrs.pop(k)

        if not attrs.get('Meta'):
            attrs['Meta'] = type('Meta', (object, ), {})
        attrs['Meta'].abstract = True

        attrs['__qualname__'] = 'Abstract' + attrs['__qualname__']
        abstract = super(ShareMeta, cls).__new__(cls, 'Abstract' + name, bases + (ShareAbstract, ), attrs)

        concrete = type(
            name,
            (ShareConcrete, abstract),
            {
                '__module__': module,
                **{k: v.for_concrete() for k, v in relations.items() if v}
            }
        )

        concrete.Abstract = abstract

        concrete.Version = type(
            name + 'Version',
            (ShareVersion, abstract),
            {
                '__module__': module,
                **{k: v.for_version() for k, v in relations.items() if v}
            }
        )

        concrete.Current = type(
            name + 'Current',
            (ShareCurrent, ),
            {
                '__module__': module,
                'version': models.ForeignKey(concrete.Version),
                **{k: v.for_current() for k, v in relations.items() if v}
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
