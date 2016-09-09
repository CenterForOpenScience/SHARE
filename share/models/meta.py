from django.db import models
from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.postgres.fields import JSONField

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareURLField, ShareManyToManyField
from share.apps import ShareConfig as share_config


__all__ = ('Venue', 'Award', 'Tag', 'Subject', 'Identifier', 'Relation', 'RelationType')

# TODO Rename this file


class Identifier(ShareObject):
    # https://twitter.com/berniethoughts/
    url = ShareURLField(unique=True)
    # https://twitter.com/
    base_url = ShareURLField()

    object_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    identified_object = GenericForeignKey('object_type', 'object_id')

    class Meta:
        index_together = ('object_type', 'object_id')


class RelationTypeManager(models.Manager):
    def get_by_natural_key(self, key):
        return self.get(key=key)


class RelationType(models.Model):
    key = models.TextField(unique=True)
    uri = models.TextField(blank=True)
    #TODO? parent = models.ForeignKey('self')

    objects = RelationTypeManager()

    def natural_key(self):
        return self.key

    @staticmethod
    def valid_natural_key(key):
        return isinstance(key, str)


class Relation(ShareObject):
    subject_work = ShareForeignKey('AbstractCreativeWork', related_name='outgoing_%(class)ss')
    object_work = ShareForeignKey('AbstractCreativeWork', related_name='incoming_%(class)ss')
    relation_type = models.ForeignKey(RelationType)

    class Meta:
        unique_together = ('subject_work', 'object_work', 'relation_type')


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
