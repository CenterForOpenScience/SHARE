from share.models.base import ShareObject, TypedShareObjectMeta
from share.models.fields import ShareForeignKey

from share.util import ModelGenerator


class AbstractWorkRelation(ShareObject, metaclass=TypedShareObjectMeta):
    subject = ShareForeignKey('AbstractCreativeWork', related_name='outgoing_creative_work_relations')
    related = ShareForeignKey('AbstractCreativeWork', related_name='incoming_creative_work_relations')

    class Disambiguation:
        all = ('subject', 'related')
        constrain_types = True

    class Meta(ShareObject.Meta):
        db_table = 'share_workrelation'
        unique_together = ('subject', 'related', 'type')


generator = ModelGenerator()
globals().update(generator.subclasses_from_yaml(__file__, AbstractWorkRelation))


__all__ = tuple(key for key, value in globals().items() if isinstance(value, type) and issubclass(value, ShareObject))
