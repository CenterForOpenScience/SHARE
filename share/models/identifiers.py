from furl import furl

from django.db import models

from share.models.base import ShareObject, ShareObjectVersion
from share.models.fields import ShareForeignKey, ShareURLField

__all__ = ('CreativeWorkIdentifier', 'PersonIdentifier')


# TODO common interface
#class Identifier(ShareObject):
#    # http://twitter.com/berniethoughts/, mailto://contact@cos.io
#    uri = ShareURLField(unique=True)
#
#    # twitter.com, cos.io
#    host = models.TextField(editable=False)
#
#    # http, mailto
#    scheme = models.TextField(editable=False)
#
#    def save(self, *args, **kwargs):
#        f = furl(self.uri)
#        self.host = f.host
#        self.scheme = f.scheme
#        super(Identifier, self).save(*args, **kwargs)
#
#    class Meta:
#        abstract = True


class CreativeWorkIdentifier(ShareObject):
    # http://twitter.com/berniethoughts/, mailto://contact@cos.io
    uri = ShareURLField(unique=True)

    # twitter.com, cos.io
    host = models.TextField(editable=False)

    # http, mailto
    scheme = models.TextField(editable=False)

    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='%(class)ss')

    def save(self, *args, **kwargs):
        f = furl(self.uri)
        self.host = f.host
        self.scheme = f.scheme
        super(CreativeWorkIdentifier, self).save(*args, **kwargs)



class PersonIdentifier(ShareObject):
    # http://twitter.com/berniethoughts/, mailto://contact@cos.io
    uri = ShareURLField(unique=True)

    # twitter.com, cos.io
    host = models.TextField(editable=False)

    # http, mailto
    scheme = models.TextField(editable=False)

    person = ShareForeignKey('Person', related_name='%(class)ss')

    def save(self, *args, **kwargs):
        f = furl(self.uri)
        self.host = f.host
        self.scheme = f.scheme
        super(PersonIdentifier, self).save(*args, **kwargs)

