from django.db import models

from django.db.models.base import ModelBase

# from share.models.base import ShareObject
# from share.models.base import ShareObjectMeta
from share.models.contributor import Person


class ShareCreativeMeta(ModelBase):

    def __new__(cls, name, bases, attrs):
        if not attrs.get('Meta'):
            attrs['Meta'] = type('Meta', (object, ), {})

        attrs['Meta'].managed = False
        attrs['Meta'].db_table = 'creative_work'

        attrs['_django_fields'] = [v for v in attrs.values() if isinstance(v, models.Field)]

        return super(ShareCreativeMeta, cls).__new__(cls, name, bases, attrs)


class AbstractCreativeWork(models.Model, metaclass=ShareCreativeMeta):
    title = models.TextField()
    description = models.TextField()
    # contributors = models.ManyToManyField(Person, through='Contributor')

    class Meta:
        abstract = True


class Preprint(AbstractCreativeWork):
    posted_date = models.DateTimeField()
