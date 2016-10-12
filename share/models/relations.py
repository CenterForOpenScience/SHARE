from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from mptt.models import MPTTModel, TreeForeignKey

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareForeignKey, ShareURLField, ShareManyToManyField


__all__ = ('WorkRelation', 'EntityRelation', 'Contribution', 'Award', 'WorkRelationType', 'EntityRelationType', 'ThroughContribution')


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


class Contribution(ShareObject, metaclass=TypedShareObjectMeta):
    creative_work = ShareForeignKey('AbstractCreativeWork')
    entity = ShareForeignKey('AbstractEntity')

    bibliographic = models.BooleanField(default=True)
    cited_as = models.TextField(blank=True)
    order_cited = models.PositiveIntegerField(null=True)

    class Meta:
        unique_together = ('entity', 'creative_work', 'type')


class ThroughContribution(ShareObject):
    origin = ShareForeignKey(Contribution, related_name='+')
    destination = ShareForeignKey(Contribution, related_name='+')

    def clean(self):
        if self.origin.creative_work != self.destination.creative_work:
            raise ValidationError(_('ThroughContributions must contribute to the same AbstractCreativeWork'))
        if self.origin.entity == self.destination.entity:
            raise ValidationError(_('A contributor may not contribute through itself'))

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class CollaboratorContribution(Contribution):
    contributed_through = ShareManyToManyField('Contribution', symmetrical=False, through='ThroughContribution', through_fields=('origin', 'destination'))


class FunderContribution(Contribution):
    awards = ShareManyToManyField('Award', through='ThroughContributionAwards')


class PublisherContribution(Contribution):
    pass


class HostContribution(Contribution):
    pass


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

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class EntityRelationType(AbstractRelationType):
    pass


class WorkRelationType(AbstractRelationType):
    pass


class ContributionType(AbstractRelationType):
    pass
