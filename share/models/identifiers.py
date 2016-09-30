import furl

from django.db import models

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareURLField

__all__ = ('CreativeWorkIdentifier', 'PersonIdentifier')


class Identifier:
    # http://twitter.com/berniethoughts/, mailto://contact@cos.io
    uri = ShareURLField(unique=True)

    # twitter.com, cos.io
    host = models.TextField(editable=False)

    # http, mailto
    scheme = models.TextField(editable=False)

    def save(self, *args, **kwargs):
        f = furl(self.uri)
        self.host = f.host
        self.scheme = f.scheme
        super(Identifier, self).save(*args, **kwargs)

    class Meta:
        abstract = True


class CreativeWorkIdentifier(ShareObject, Identifier):
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='identifiers')


class PersonIdentifier(ShareObject, Identifier):
    person = ShareForeignKey('Person', related_name='identifiers')
