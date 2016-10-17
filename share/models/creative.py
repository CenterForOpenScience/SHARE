from django.db import models

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.meta import Venue, Tag, Subject
from share.models.fields import ShareManyToManyField, ShareURLField

from share.util import ModelGenerator


# Base Creative Work class

class AbstractCreativeWork(ShareObject, metaclass=TypedShareObjectMeta):
    title = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)  # Used to determine if something should be surfaced in ES or not  this may need to be renamed later
    date_published = models.DateTimeField(null=True)
    date_updated = models.DateTimeField(null=True)
    free_to_read_type = ShareURLField(blank=True)
    free_to_read_date = models.DateTimeField(null=True)
    rights = models.TextField(blank=True, null=True)
    language = models.TextField(blank=True, null=True)

    subjects = ShareManyToManyField(Subject, related_name='subjected_works', through='ThroughSubjects')
    tags = ShareManyToManyField(Tag, related_name='tagged_works', through='ThroughTags')

    venues = ShareManyToManyField(Venue, through='ThroughVenues')

    related_agents = ShareManyToManyField('AbstractAgent', through='AbstractAgentWorkRelation')
    related_works = ShareManyToManyField('AbstractCreativeWork', through='AbstractWorkRelation', through_fields=('subject', 'related'), symmetrical=False)

    def __str__(self):
        return self.title

generator = ModelGenerator()
globals().update(generator.subclasses_from_yaml(__file__, AbstractCreativeWork))
