from django.db import models

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta


class AbstractCreativeWork(ShareObject, metaclass=TypedShareObjectMeta):
    title = models.TextField()
    description = models.TextField()
    contributors = models.ManyToManyField('Person', through='Contributor')


class CreativeWork(AbstractCreativeWork):
    pass
