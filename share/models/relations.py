import json

from model_utils import Choices

from django.db import models

from mptt.models import MPTTModel, TreeForeignKey

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareURLField, ShareManyToManyField

__all__ = ('WorkRelation', 'EntityRelation', 'Contribution', 'Award')


class WorkRelation(ShareObject):
    from_work = ShareForeignKey('AbstractCreativeWork', related_name='outgoing_%(class)ss')
    to_work = ShareForeignKey('AbstractCreativeWork', related_name='incoming_%(class)ss')
    relation_type = models.ForeignKey('WorkRelationType')

    class Meta:
        unique_together = ('from_work', 'to_work', 'relation_type')


class EntityRelation(ShareObject):
    from_entity = ShareForeignKey('AbstractEntity', related_name='outgoing_%(class)ss')
    to_entity = ShareForeignKey('AbstractEntity', related_name='incoming_%(class)ss')
    relation_type = models.ForeignKey('EntityRelationType')

    class Meta:
        unique_together = ('from_entity', 'to_entity', 'relation_type')


class Contribution(ShareObject):
    entity = ShareForeignKey('AbstractEntity')
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='%(class)ss')
    contribution_type = models.ForeignKey('ContributionType', related_name='%(class)ss')

    cited_name = models.TextField(blank=True)
    bibliographic = models.BooleanField(default=True)
    order_cited = models.PositiveIntegerField(null=True)

    awards = ShareManyToManyField('Award', through='ThroughContributionAwards')

    class Meta:
        # TODO also contribution_type? Do we want to let one entity contribute in multiple ways?
        unique_together = ('entity', 'creative_work')


class Award(ShareObject):
    # ScholarlyArticle has an award object
    # it's just a text field, I assume our 'description' covers it.
    name = models.TextField(blank=True)
    description = models.TextField(blank=True)
    url = ShareURLField(blank=True)

    def __str__(self):
        return self.description


class ThroughContributionAwards(ShareObject):
    contribution = ShareForeignKey(Contribution)
    award = ShareForeignKey(Award)

    class Meta:
        unique_together = ('contribution', 'award')


class WorkRelationType(MPTTModel):
    name = models.TextField(unique=True)
    parent = TreeForeignKey('self', null=True, related_name='children', db_index=True)
    uris = models.JSONField()
    

class EntityRelationType(MPTTModel):
    name = models.TextField(unique=True)
    parent = TreeForeignKey('self', null=True, related_name='children', db_index=True)
    uris = models.JSONField()


class ContributionType(MPTTModel):
    name = models.TextField(unique=True)
    parent = TreeForeignKey('self', null=True, related_name='children', db_index=True)
    uris = models.JSONField()
