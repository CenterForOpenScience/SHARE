import json

from model_utils import Choices

from django.db import models
from django.contrib.postgres.fields import JSONField

from mptt.models import MPTTModel, TreeForeignKey

from share.models.base import ShareObject
from share.models.fields import ShareForeignKey, ShareURLField, ShareManyToManyField

__all__ = ('WorkRelation', 'EntityRelation', 'Contribution', 'Award', 'WorkRelationType', 'EntityRelationType', 'ContributionType')


class WorkRelation(ShareObject):
    from_work = ShareForeignKey('AbstractCreativeWork', related_name='outgoing_%(class)ss')
    to_work = ShareForeignKey('AbstractCreativeWork', related_name='incoming_%(class)ss')
    relation_type = TreeForeignKey('WorkRelationType')

    class Meta:
        unique_together = ('from_work', 'to_work', 'relation_type')


class EntityRelation(ShareObject):
    from_entity = ShareForeignKey('AbstractEntity', related_name='outgoing_%(class)ss')
    to_entity = ShareForeignKey('AbstractEntity', related_name='incoming_%(class)ss')
    relation_type = TreeForeignKey('EntityRelationType')

    class Meta:
        unique_together = ('from_entity', 'to_entity', 'relation_type')


class Contribution(ShareObject):
    entity = ShareForeignKey('AbstractEntity')
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='%(class)ss')
    contribution_type = TreeForeignKey('ContributionType', related_name='%(class)ss')

    cited_name = models.TextField(blank=True)
    bibliographic = models.BooleanField(default=True)
    order_cited = models.PositiveIntegerField(null=True)

    awards = ShareManyToManyField('Award', through='ThroughContributionAwards')

    class Meta:
        unique_together = ('entity', 'creative_work', 'contribution_type')


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


class AbstractRelationType(MPTTModel):
    name = models.TextField(unique=True)
    uris = JSONField(editable=False)
    parent = TreeForeignKey('self', null=True, related_name='children', db_index=True, editable=False)

    class Meta:
        abstract = True


class EntityRelationType(AbstractRelationType):
    pass


class WorkRelationType(AbstractRelationType):
    pass


class ContributionType(AbstractRelationType):
    pass
