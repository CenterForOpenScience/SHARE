from share.models.base import ShareObject, TypedShareObjectMeta
from share.models.fields import ShareForeignKey

from share.util import ModelGenerator


class AbstractWorkRelation(ShareObject, metaclass=TypedShareObjectMeta):
    from_work = ShareForeignKey('AbstractCreativeWork', related_name='outgoing_%(class)ss')
    to_work = ShareForeignKey('AbstractCreativeWork', related_name='incoming_%(class)ss')

    class Meta:
        unique_together = ('from_work', 'to_work', 'type')


generator = ModelGenerator()
globals().update(generator.subclasses_from_yaml(__file__, AbstractWorkRelation))
