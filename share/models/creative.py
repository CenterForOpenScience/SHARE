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

    # Used to determine if something should be surfaced in ES or not
    # this may need to be renamed later
    is_deleted = models.BooleanField(default=False)

    contributors = ShareManyToManyField('AbstractEntity', through='Contribution')

    subjects = ShareManyToManyField(Subject, related_name='subjected_%(class)s', through='ThroughSubjects')
    tags = ShareManyToManyField(Tag, related_name='tagged_%(class)s', through='ThroughTags')

    venues = ShareManyToManyField(Venue, through='ThroughVenues')

    related_works = ShareManyToManyField('AbstractCreativeWork', through='WorkRelation', through_fields=('from_work', 'to_work'), symmetrical=False)

    date_published = models.DateTimeField(null=True, db_index=True)
    date_updated = models.DateTimeField(null=True, db_index=True)
    free_to_read_type = ShareURLField(blank=True, db_index=True)
    free_to_read_date = models.DateTimeField(null=True, db_index=True)

    rights = models.TextField(blank=True, null=True, db_index=True)
    language = models.TextField(blank=True, null=True, db_index=True)

    def __str__(self):
        return self.title


generator = ModelGenerator()
globals().update(generator.subclasses_from_yaml(__file__, AbstractCreativeWork))
