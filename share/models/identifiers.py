from furl import furl

from django.db import models
from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareURLField

__all__ = ('WorkIdentifier', 'AgentIdentifier')


# TODO Common interface, so we're not duplicating code. Doesn't work because
# ShareObjectMeta doesn't look at bases when building Version classes.
#
# class Identifier(ShareObject):
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


class WorkIdentifier(ShareObject):
    uri = ShareURLField(unique=True)
    host = models.TextField(editable=False)
    scheme = models.TextField(editable=False)
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='identifiers')

    def save(self, *args, **kwargs):
        f = furl(self.uri)
        self.host = f.host
        self.scheme = f.scheme
        super(WorkIdentifier, self).save(*args, **kwargs)

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.uri, self.creative_work_id)


class AgentIdentifier(ShareObject):
    uri = ShareURLField(unique=True)
    host = models.TextField(editable=False)
    scheme = models.TextField(editable=False)
    agent = ShareForeignKey('AbstractAgent', related_name='identifiers')

    def save(self, *args, **kwargs):
        f = furl(self.uri)
        self.host = f.host
        self.scheme = f.scheme
        super(AgentIdentifier, self).save(*args, **kwargs)

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.uri, self.agent_id)
