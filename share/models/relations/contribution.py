from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from share.models.base import ShareObject, ShareObjectVersion, TypedShareObjectMeta
from share.models.fields import ShareForeignKey, ShareURLField, ShareManyToManyField

from share.util import ModelGenerator


class AbstractAgentWorkRelation(ShareObject, metaclass=TypedShareObjectMeta):
    creative_work = ShareForeignKey('AbstractCreativeWork', related_name='agent_relations')
    agent = ShareForeignKey('AbstractAgent', related_name='work_relations')

    bibliographic = models.BooleanField(default=True)
    cited_as = models.TextField(blank=True)
    order_cited = models.PositiveIntegerField(null=True)

    class Meta:
        unique_together = ('agent', 'creative_work', 'type')


class ThroughContribution(ShareObject):
    subject = ShareForeignKey(AbstractAgentWorkRelation, related_name='+')
    related = ShareForeignKey(AbstractAgentWorkRelation, related_name='+')

    def clean(self):
        if self.subject.creative_work != self.related.creative_work:
            raise ValidationError(_('ThroughContributions must contribute to the same AbstractCreativeWork'))
        if self.subject.agent == self.related.agent:
            raise ValidationError(_('A contributor may not contribute through itself'))

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class Award(ShareObject):
    # ScholarlyArticle has an award object
    # it's just a text field, I assume our 'description' covers it.
    name = models.TextField(blank=True)
    description = models.TextField(blank=True)
    url = ShareURLField(blank=True)

    def __str__(self):
        return self.description


class ThroughContributionAwards(ShareObject):
    contribution = ShareForeignKey(AbstractAgentWorkRelation)
    award = ShareForeignKey(Award)

    class Meta:
        unique_together = ('contribution', 'award')


generator = ModelGenerator(field_types={
    'm2m': ShareManyToManyField
})
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgentWorkRelation))

__all__ = tuple(key for key, value in globals().items() if isinstance(value, type) and issubclass(value, (ShareObject, ShareObjectVersion)))
