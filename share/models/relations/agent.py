from share.models.base import ShareObject, TypedShareObjectMeta
from share.models.fields import ShareForeignKey

from share.util import ModelGenerator


class AbstractAgentRelation(ShareObject, metaclass=TypedShareObjectMeta):
    subject = ShareForeignKey('AbstractAgent', related_name='+')
    related = ShareForeignKey('AbstractAgent', related_name='+')

    class Disambiguation:
        all = ('subject', 'related')
        constrain_types = True

    class Meta:
        db_table = 'share_agentrelation'
        unique_together = ('subject', 'related', 'type')


generator = ModelGenerator()
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgentRelation))


__all__ = tuple(key for key, value in globals().items() if isinstance(value, type) and issubclass(value, ShareObject))
