from share.models.base import ShareObject, TypedShareObjectMeta
from share.models.fields import ShareForeignKey, ShareURLField, ShareManyToManyField

from share.util import ModelGenerator


class AbstractEntityRelation(ShareObject, metaclass=TypedShareObjectMeta):
    from_entity = ShareForeignKey('AbstractEntity', related_name='outgoing_%(class)ss')
    to_entity = ShareForeignKey('AbstractEntity', related_name='incoming_%(class)ss')

    class Meta:
        unique_together = ('from_entity', 'to_entity', 'type')


generator = ModelGenerator()
globals().update(generator.subclasses_from_yaml(__file__, AbstractEntityRelation))
