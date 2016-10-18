import nameparser

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from nameparser import HumanName

from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareManyToManyField

from share.util import ModelGenerator


class AbstractAgent(ShareObject, metaclass=TypedShareObjectMeta):
    """
    An Agent is a thing that has the power to act, to make decisions,
    to produce or contribute to the production of creative works.
    Either an individual person or a group of people.
    """

    name = models.TextField(blank=True)
    location = models.TextField(blank=True)
    related_agents = ShareManyToManyField('AbstractAgent', through='AbstractAgentRelation', through_fields=('subject', 'related'), symmetrical=False)
    related_works = ShareManyToManyField('AbstractCreativeWork', through='AbstractAgentWorkRelation')

    class Meta:
        db_table = 'share_agent'
        index_together = (
            ('type', 'name',)
        )

    def __str__(self):
        return self.name


@receiver(pre_save, sender='Person')
def parse_person_name(sender, instance, *args, **kwargs):
    if instance.name and instance.family_name is None and instance.given_name is None:
        name = HumanName(instance.name)
        instance.family_name = name.last
        instance.given_name = name.first
        instance.suffix = name.suffix
        instance.additional_name = name.middle


generator = ModelGenerator(field_types={
    'text': models.TextField
})
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgent))


@receiver(pre_save, sender=Person, dispatch_uid='share.share.models.share_person_post_save_handler')  # noqa
def person_post_save(sender, instance, **kwargs):
    if not instance.name:
        instance.name = ' '.join(x for x in (instance.given_name, instance.additional_name, instance.family_name, instance.suffix) if x)
    if not any((instance.given_name, instance.additional_name, instance.given_name, instance.suffix)):
        name = nameparser.HumanName(instance.name)
        instance.given_name = name.first
        instance.family_name = name.last
        instance.additional_name = name.middle
        instance.suffix = name.suffix
