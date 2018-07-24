from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from share.disambiguation.criteria import MatchAgentWorkRelations, MatchByAttrs, MatchByManyToOne
from share.models.base import ShareObject, ShareObjectVersion, TypedShareObjectMeta
from share.models.fields import ShareForeignKey, ShareURLField, ShareManyToManyField

from share.util import ModelGenerator


class AbstractAgentWorkRelation(ShareObject, metaclass=TypedShareObjectMeta):
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='agent_relations')
    agent = ShareForeignKey('AbstractAgent', related_name='work_relations')

    cited_as = models.TextField(blank=True)

    matching_criteria = [
        MatchByManyToOne('creative_work', 'agent', constrain_types=True),
        MatchAgentWorkRelations(),
    ]

    class Meta(ShareObject.Meta):
        db_table = 'share_agentworkrelation'
        unique_together = ('agent', 'creative_work', 'type')


class ThroughContributor(ShareObject):
    subject = ShareForeignKey(AbstractAgentWorkRelation, related_name='+')
    related = ShareForeignKey(AbstractAgentWorkRelation, related_name='+')

    def clean(self):
        if self.subject.creative_work != self.related.creative_work:
            raise ValidationError(_('ThroughContributors must contribute to the same AbstractCreativeWork'))
        if self.subject.agent == self.related.agent:
            raise ValidationError(_('A contributor may not contribute through itself'))

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    matching_criteria = MatchByManyToOne('subject', 'related')

    class Meta(ShareObject.Meta):
        unique_together = ('subject', 'related')


class Award(ShareObject):
    # ScholarlyArticle has an award object
    # it's just a text field, I assume our 'description' covers it.
    name = models.TextField(blank=True)
    description = models.TextField(blank=True)
    date = models.DateTimeField(blank=True, null=True)
    award_amount = models.PositiveIntegerField(blank=True, null=True)
    uri = ShareURLField(unique=True, blank=True, null=True)

    def __str__(self):
        return self.description

    matching_criteria = MatchByAttrs('uri')


class ThroughAwards(ShareObject):
    funder = ShareForeignKey(AbstractAgentWorkRelation)
    award = ShareForeignKey(Award)

    class Meta(ShareObject.Meta):
        unique_together = ('funder', 'award')
        verbose_name_plural = 'through awards'

    matching_criteria = MatchByManyToOne('funder', 'award')


generator = ModelGenerator(field_types={
    'm2m': ShareManyToManyField,
    'positive_int': models.PositiveIntegerField
})
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgentWorkRelation))

__all__ = tuple(key for key, value in globals().items() if isinstance(value, type) and issubclass(value, (ShareObject, ShareObjectVersion)))
