import factory
from factory import fuzzy
from factory.django import DjangoModelFactory

from django.contrib.contenttypes.models import ContentType

from share import models

from tests.factories.core import NormalizedDataFactory


__all__ = (
    'ChangeFactory',
    'ChangeSetFactory',
)


class ChangeSetFactory(DjangoModelFactory):
    normalized_data = factory.SubFactory(NormalizedDataFactory)

    class Meta:
        model = models.ChangeSet


class ChangeFactory(DjangoModelFactory):
    type = fuzzy.FuzzyChoice(models.Change.TYPE._db_values)
    change = {}
    node_id = factory.Sequence(lambda x: x)
    change_set = factory.SubFactory(ChangeSetFactory)
    target_type = factory.Iterator(ContentType.objects.all())
    target_version_type = factory.Iterator(ContentType.objects.all())

    @factory.lazy_attribute
    def model_type(self, *args, **kwargs):
        return self.target_type

    class Meta:
        model = models.Change
