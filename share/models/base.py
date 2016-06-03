import uuid
import inspect

from django.db import models
from django.db import transaction
from django.db.models.base import ModelBase
from django.contrib.auth.models import User


class ShareAbstract:
    pass


class ShareVersion(models.Model):
    id = models.AutoField(primary_key=True)
    # created_by = models.ForeignKey(User)  TODO
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

    class Meta:
        abstract = True

    # TODO Tag w/ user
    @transaction.atomic
    def save(self):
        data = {field.attname: getattr(self, field.attname) for field in self._meta.fields}
        data['persistant_id'] = data.pop('id')
        version = self.__class__.Version(**data)
        version.save()
        self.__class__.Current(id=self.id, version=version).save()
        return super().save()


class ShareMeta(ModelBase):

    def __new__(cls, name, bases, attrs):
        if models.Model in bases or len(bases) > 1:
            return super(ShareMeta, cls).__new__(cls, name, bases, attrs)

        module = attrs['__module__']

        if not attrs.get('Meta'):
            attrs['Meta'] = type('Meta', (object, ), {})
        attrs['Meta'].abstract = True

        attrs['__qualname__'] = 'Abstract' + attrs['__qualname__']
        abstract = super(ShareMeta, cls).__new__(cls, 'Abstract' + name, bases + (ShareAbstract, ), attrs)
        concrete = type(name, (ShareConcrete, abstract), {'__module__': module})

        concrete.Abstract = abstract

        concrete.Version = type(
            name + 'Version',
            (ShareVersion, abstract),
            {'__module__': module}
        )

        concrete.Current = type(
            name + 'Current',
            (ShareCurrent, abstract),
            {
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
