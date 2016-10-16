import random

import factory
from factory import fuzzy
from factory.django import DjangoModelFactory

from django.contrib.contenttypes.models import ContentType

from share import models


class ShareUserFactory(DjangoModelFactory):
    username = factory.Sequence(lambda x: x)

    class Meta:
        model = models.ShareUser


class NormalizedDataFactory(DjangoModelFactory):
    normalized_data = {}
    source = factory.SubFactory(ShareUserFactory)

    class Meta:
        model = models.NormalizedData


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

    class Meta:
        model = models.Change


class ShareObjectFactory(DjangoModelFactory):
    change = factory.SubFactory(ChangeFactory)

    class Meta:
        abstract = True

    @classmethod
    def _after_postgeneration(cls, obj, create, results=None):
        return

    @classmethod
    def _create(cls, obj, **attrs):
        for key, value in tuple(attrs.items()):
            if hasattr(value, 'VersionModel'):
                attrs[key + '_version'] = value.versions.first()
        return super()._create(obj, **attrs)

    @factory.post_generation
    def setup_change(self, create, extracted, **kwargs):
        self.refresh_from_db()
        self.change.target = self
        self.change.target_version = self.version
        self.change.save()


class TypedShareObjectFactory(ShareObjectFactory):
    class Meta:
        abstract = True

    @factory.lazy_attribute
    def type(stub):
        return random.choice([m.label.lower() for m in stub._LazyStub__model_class._meta.model._meta.concrete_model._meta.proxied_children])


class EntityFactory(TypedShareObjectFactory):
    name = factory.Faker('company')
    given_name = factory.Faker('first_name')
    family_name = factory.Faker('last_name')

    class Meta:
        model = models.AbstractEntity


class AbstractCreativeWorkFactory(TypedShareObjectFactory):
    title = factory.Faker('sentence')
    description = factory.Faker('paragraph')

    class Meta:
        model = models.AbstractCreativeWork

    @factory.post_generation
    def contributions(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if isinstance(extracted, int):
            for _ in range(0, extracted):
                EntityWorkRelationFactory(creative_work=self)


class EntityWorkRelationFactory(TypedShareObjectFactory):
    entity = factory.SubFactory(EntityFactory)
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = models.EntityWorkRelation


class PreprintFactory(AbstractCreativeWorkFactory):
    type = 'share.preprint'


class ThroughEntityWorkRelationFactory(ShareObjectFactory):
    subject = factory.SubFactory(EntityWorkRelationFactory)
    related = factory.SubFactory(EntityWorkRelationFactory)

    class Meta:
        model = models.ThroughContribution
