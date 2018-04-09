from share.models.base import ShareObject, TypedShareObjectMeta
from share.models.fields import ShareForeignKey

from share.util import ModelGenerator


class AbstractAgentRelation(ShareObject, metaclass=TypedShareObjectMeta):
    subject = ShareForeignKey('AbstractAgent', related_name='outgoing_agent_relations')
    related = ShareForeignKey('AbstractAgent', related_name='incoming_agent_relations')

    class Disambiguation:
        all = ('subject', 'related')
        constrain_types = True

    class Meta(ShareObject.Meta):
        db_table = 'share_agentrelation'
        unique_together = ('subject', 'related', 'type')


generator = ModelGenerator()
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgentRelation))


__all__ = tuple(key for key, value in globals().items() if isinstance(value, type) and issubclass(value, ShareObject))
