from share.models.base import ShareObject, TypedShareObjectMeta
from share.models.fields import ShareForeignKey

from share.util import ModelGenerator


class AbstractAgentRelation(ShareObject, metaclass=TypedShareObjectMeta):
    subject = ShareForeignKey('AbstractAgent', related_name='+')
    related = ShareForeignKey('AbstractAgent', related_name='+')

    class Meta:
        # default_related_name = 'agent_relations'
        unique_together = ('subject', 'related', 'type')


generator = ModelGenerator()
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgentRelation))


__all__ = tuple(key for key, value in globals().items() if isinstance(value, type) and issubclass(value, ShareObject))
