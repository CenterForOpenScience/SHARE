import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _

from share.transform.chain.links import IRILink
from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareURLField

logger = logging.getLogger('share.normalize')
__all__ = ('WorkIdentifier', 'AgentIdentifier', 'WorkIdentifierVersion', 'AgentIdentifierVersion')  # noqa


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

class FilteredEmailsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(scheme='mailto')


class WorkIdentifier(ShareObject):
    """
    Unique identifier (in IRI form) for a creative work.
    """
    uri = ShareURLField(unique=True)
    host = models.TextField(editable=False)
    scheme = models.TextField(editable=False, help_text=_('A prefix to URI indicating how the following data should be interpreted.'))
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='identifiers')

    # objects = FilteredEmailsManager()
    # objects_unfiltered = models.Manager()

    @classmethod
    def normalize(self, node, graph):
        try:
            ret = IRILink().execute(node.attrs['uri'])
        except ValueError as e:
            logger.warning('Discarding invalid identifier %s with error %s', node.attrs['uri'], e)
            graph.remove(node)
            return

        if ret['authority'] in {'issn', 'orcid.org'} or ret['scheme'] in {'mailto'}:
            logger.warning('Discarding %s %s as an invalid identifier for works', ret['authority'], ret['IRI'])
            graph.remove(node)
            return

        if node.attrs['uri'] != ret['IRI']:
            logger.debug('Normalized %s to %s', node.attrs['uri'], ret['IRI'])

        node.attrs = {
            'uri': ret['IRI'],
            'host': ret['authority'],
            'scheme': ret['scheme'],
        }

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.uri, self.creative_work_id)

    class Disambiguation:
        all = ('uri',)


class AgentIdentifier(ShareObject):
    """Unique identifier (in IRI form) for an agent."""
    uri = ShareURLField(unique=True)
    host = models.TextField(editable=False)
    scheme = models.TextField(editable=False)
    agent = ShareForeignKey('AbstractAgent', related_name='identifiers')

    # objects = FilteredEmailsManager()
    # objects_unfiltered = models.Manager()

    @classmethod
    def normalize(self, node, graph):
        try:
            ret = IRILink().execute(node.attrs['uri'])
        except ValueError as e:
            logger.warning('Discarding invalid identifier %s with error %s', node.attrs['uri'], e)
            graph.remove(node)
            return

        if node.attrs['uri'] != ret['IRI']:
            logger.debug('Normalized %s to %s', node.attrs['uri'], ret['IRI'])

        node.attrs = {
            'uri': ret['IRI'],
            'host': ret['authority'],
            'scheme': ret['scheme'],
        }

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.uri, self.agent_id)

    class Disambiguation:
        all = ('uri',)
