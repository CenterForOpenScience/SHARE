import logging


from share.models.base import ShareObject, TypedShareObjectMeta
from share.models.fields import ShareForeignKey

from share.util import ModelGenerator


logger = logging.getLogger('share.normalize')


class AbstractAgentRelation(ShareObject, metaclass=TypedShareObjectMeta):
    subject = ShareForeignKey('AbstractAgent', related_name='outgoing_agent_relations')
    related = ShareForeignKey('AbstractAgent', related_name='incoming_agent_relations')

    class Disambiguation:
        all = ('subject', 'related')
        constrain_types = True

    class Meta:
        db_table = 'share_agentrelation'
        unique_together = ('subject', 'related', 'type')

    @classmethod
    def normalize(self, node, graph):
        if len(node.related()) < 2:
            logger.warning('Removing incomplete or circular relation %s, %s', node, node.related())
            graph.remove(node)


generator = ModelGenerator()
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgentRelation))


__all__ = tuple(key for key, value in globals().items() if isinstance(value, type) and issubclass(value, ShareObject))
