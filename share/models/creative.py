from django.db import models

from share.models.base import ShareObject
from share.models.people import Person
from share.models.base import TypedShareObjectMeta
from share.models.meta import Venue, Award, Tag
from share.models.fields import ShareForeignKey, ShareManyToManyField, ShareURLField


# Base Creative Work class

class AbstractCreativeWork(ShareObject, metaclass=TypedShareObjectMeta):
    title = models.TextField()
    description = models.TextField()

    contributors = ShareManyToManyField(Person, through='Contributor')

    awards = ShareManyToManyField(Award, through='ThroughAwards')
    venues = ShareManyToManyField(Venue, through='ThroughVenues')

    links = ShareManyToManyField('Link', through='ThroughLinks')

    funders = ShareManyToManyField('Funder', through='Association')
    publishers = ShareManyToManyField('Publisher', through='Association')
    institutions = ShareManyToManyField('Institution', through='Association')
    organizations = ShareManyToManyField('Organization', through='Association')

    subject = ShareForeignKey(Tag, related_name='subjected_%(class)s', null=True)
    # Note: Null allows inserting of None but returns it as an empty string
    tags = ShareManyToManyField(Tag, related_name='tagged_%(class)s', through='ThroughTags')
    date_created = models.DateTimeField(null=True, db_index=True)
    date_published = models.DateTimeField(null=True, db_index=True)
    date_updated = models.DateTimeField(null=True, db_index=True)
    free_to_read_type = ShareURLField(blank=True, db_index=True)
    free_to_read_date = models.DateTimeField(null=True, db_index=True)

    rights = models.TextField(blank=True, null=True, db_index=True)
    language = models.TextField(blank=True, null=True, db_index=True)

    def __str__(self):
        return self.title


# Subclasses/Types of Creative Work

class CreativeWork(AbstractCreativeWork):
    pass


class Preprint(AbstractCreativeWork):
    pass


class Manuscript(AbstractCreativeWork):
    pass


class Publication(AbstractCreativeWork):
    pass


class Project(AbstractCreativeWork):
    pass


class Registration(AbstractCreativeWork):
    pass


# Through Tables for Creative Work

class Association(ShareObject):
    entity = ShareForeignKey('Entity')
    creative_work = ShareForeignKey(AbstractCreativeWork)

    class Meta:
        unique_together = ('entity', 'creative_work')

    def __str__(self):
        return str(self.entity)
