import furl
import json

from django.db import models
from django.db import IntegrityError
from django.contrib.postgres.fields import JSONField

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareURLField, ShareManyToManyField


__all__ = ('Venue', 'Award', 'Tag', 'Subject', 'Identifier', 'Relation')

# TODO Rename this file


class Identifier(ShareObject):
    # https://twitter.com/berniethoughts/
    url = ShareURLField(unique=True)

    # https://twitter.com/
    def get_base_url(self):
        return furl(self.url).origin


class Relation(ShareObject):
    with open('./share/models/relation-types.json') as fobj:
        # TODO add label to file
        RELATION_TYPES = [(t['key'], t['uri']) for t in json.load(fobj)]

    from_work = ShareForeignKey('AbstractCreativeWork', related_name='outgoing_%(class)ss')
    to_work = ShareForeignKey('AbstractCreativeWork', related_name='incoming_%(class)ss')
    relation_type = models.TextField(choices=RELATION_TYPES, blank=True)

    class Meta:
        unique_together = ('from_work', 'to_work', 'relation_type')


class Venue(ShareObject):
    name = models.TextField(blank=True)
    venue_type = ShareURLField(blank=True)
    location = ShareURLField(blank=True)
    community_identifier = ShareURLField(blank=True)

    def __str__(self):
        return self.name


class Award(ShareObject):
    # ScholarlyArticle has an award object
    # it's just a text field, I assume our 'description' covers it.
    name = models.TextField(blank=True)
    description = models.TextField(blank=True)
    url = ShareURLField(blank=True)
    entities = ShareManyToManyField('Entity', through='ThroughAwardEntities')

    def __str__(self):
        return self.description


class Tag(ShareObject):
    name = models.TextField(unique=True)

    def __str__(self):
        return self.name


class SubjectManager(models.Manager):
    def get_by_natural_key(self, subject):
        return self.get(name=subject)


class Subject(models.Model):
    lineages = JSONField(editable=False)
    parents = models.ManyToManyField('self')
    name = models.TextField(unique=True, db_index=True)

    objects = SubjectManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name

    def save(self):
        raise IntegrityError('Subjects are an immutable set! Do it in bulk, if you must.')


# Through Tables for all the things

class ThroughVenues(ShareObject):
    venue = ShareForeignKey(Venue)
    creative_work = ShareForeignKey('AbstractCreativeWork')

    class Meta:
        unique_together = ('venue', 'creative_work')


class ThroughAwards(ShareObject):
    award = ShareForeignKey(Award)
    creative_work = ShareForeignKey('AbstractCreativeWork')

    class Meta:
        unique_together = ('award', 'creative_work')


class ThroughTags(ShareObject):
    tag = ShareForeignKey(Tag)
    creative_work = ShareForeignKey('AbstractCreativeWork')

    class Meta:
        unique_together = ('tag', 'creative_work')


class ThroughAwardEntities(ShareObject):
    award = ShareForeignKey('Award')
    entity = ShareForeignKey('Entity')

    class Meta:
        unique_together = ('award', 'entity')


class ThroughSubjects(ShareObject):
    subject = models.ForeignKey('Subject')
    creative_work = ShareForeignKey('AbstractCreativeWork')

    class Meta:
        unique_together = ('subject', 'creative_work')


class WorkIdentifier(ShareObject):
    creative_work = ShareForeignKey('AbstractCreativeWork')
    identifier = ShareForeignKey('Identifier')

    class Meta:
        unique_together = ('creative_work', 'identifier')
