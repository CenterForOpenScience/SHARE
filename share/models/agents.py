from django.db import models

from share.disambiguation.criteria import MatchByAttrs, MatchByOneToMany
from share.models.base import ShareObject
from share.models.base import TypedShareObjectMeta
from share.models.fields import ShareManyToManyField
from share.util import ModelGenerator


class AbstractAgent(ShareObject, metaclass=TypedShareObjectMeta):
    """
    An Agent is an entity that has the power to act, e.g. an individual person or a group of people.

    Agents make decisions and produce or contribute to the production of creative works.
    """

    name = models.TextField(blank=True, db_index=True)
    location = models.TextField(blank=True)
    related_agents = ShareManyToManyField('AbstractAgent', through='AbstractAgentRelation', through_fields=('subject', 'related'), symmetrical=False)
    related_works = ShareManyToManyField('AbstractCreativeWork', through='AbstractAgentWorkRelation')

    matching_criteria = MatchByOneToMany('identifiers')

    class Meta(ShareObject.Meta):
        db_table = 'share_agent'
        index_together = (
            ('type', 'name',)
        )

    def __str__(self):
        return self.name


generator = ModelGenerator(field_types={
    'text': models.TextField
})
globals().update(generator.subclasses_from_yaml(__file__, AbstractAgent))


def add_unique_name_criteria(*model_classes):
    match_by_identifiers_or_name = [
        AbstractAgent.matching_criteria,
        MatchByAttrs('name', allowed_models=model_classes),
    ]
    for model_class in model_classes:
        model_class.matching_criteria = match_by_identifiers_or_name

add_unique_name_criteria(Institution, Organization, Consortium) # noqa

Department.matching_criteria = AbstractAgent.matching_criteria # noqa
