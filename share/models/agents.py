from django.db import models

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareManyToManyField

from share.util import ModelGenerator


class AbstractAgent(ShareObject, metaclass=TypedShareObjectMeta):
    name = models.TextField(blank=True)
    location = models.TextField(blank=True)
    related_entities = ShareManyToManyField('AbstractAgent', through='AbstractAgentRelation', through_fields=('subject', 'related'), symmetrical=False)
    related_works = ShareManyToManyField('AbstractCreativeWork', through='AbstractAgentWorkRelation')

    class Meta:
        verbose_name_plural = 'AbstractEntities'
        index_together = (
            ('type', 'name',)
        )

    def __str__(self):
        return self.name


generator = ModelGenerator(field_types={
    'text': models.TextField
})
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgent))
