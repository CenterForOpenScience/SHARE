import logging

from share.models.base import ShareObject, TypedShareObjectMeta
from share.models.fields import ShareForeignKey

from share.util import ModelGenerator


logger = logging.getLogger('share.normalize')


class AbstractWorkRelation(ShareObject, metaclass=TypedShareObjectMeta):
    subject = ShareForeignKey('AbstractCreativeWork', related_name='outgoing_creative_work_relations')
    related = ShareForeignKey('AbstractCreativeWork', related_name='incoming_creative_work_relations')

    class Disambiguation:
        all = ('subject', 'related')
        constrain_types = True

    class Meta:
        db_table = 'share_workrelation'
        unique_together = ('subject', 'related', 'type')

    @classmethod
    def normalize(self, node, graph):
        if len(node.related()) < 2:
            logger.warning('Removing incomplete or circular relation %s, %s', node, node.related())
            graph.remove(node)


generator = ModelGenerator()
globals().update(generator.subclasses_from_yaml(__file__, AbstractWorkRelation))


__all__ = tuple(key for key, value in globals().items() if isinstance(value, type) and issubclass(value, ShareObject))
