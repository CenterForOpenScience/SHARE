from django.db import models

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareManyToManyField

from share.util import ModelGenerator


class AbstractAgent(ShareObject, metaclass=TypedShareObjectMeta):
    """
    An Agent is a thing that has the power to act, to make decisions,
    to produce or contribute to the production of creative works.
    Either an individual person or a group of people.
    """

    name = models.TextField(blank=True)
    location = models.TextField(blank=True)
    related_agents = ShareManyToManyField('AbstractAgent', through='AbstractAgentRelation', through_fields=('subject', 'related'), symmetrical=False)
    related_works = ShareManyToManyField('AbstractCreativeWork', through='AbstractAgentWorkRelation')

    class Meta:
        index_together = (
            ('type', 'name',)
        )

    def __str__(self):
        return self.name


generator = ModelGenerator(field_types={
    'text': models.TextField
})
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgent))
