import random
from datetime import timezone

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
    data = {}
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

    @factory.lazy_attribute
    def model_type(self, *args, **kwargs):
        return self.target_type

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
                attrs[key + '_version'] = value.version
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
        model = random.choice(stub._LazyStub__model_class._meta.model._meta.concrete_model.get_type_classes())
        return model._meta.label.lower()


class AgentFactory(TypedShareObjectFactory):
    name = factory.Faker('company')
    given_name = factory.Faker('first_name')
    family_name = factory.Faker('last_name')

    class Meta:
        model = models.AbstractAgent


class AbstractCreativeWorkFactory(TypedShareObjectFactory):
    title = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    date_updated = factory.Faker('date_time_this_decade', tzinfo=timezone.utc)
    date_published = factory.Faker('date_time_this_decade', tzinfo=timezone.utc)

    class Meta:
        model = models.AbstractCreativeWork

    @factory.post_generation
    def contributors(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if isinstance(extracted, int):
            for _ in range(0, extracted):
                AgentWorkRelationFactory(creative_work=self)


class AgentWorkRelationFactory(TypedShareObjectFactory):
    cited_as = factory.Faker('name')
    agent = factory.SubFactory(AgentFactory)
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = models.AgentWorkRelation


class PreprintFactory(AbstractCreativeWorkFactory):
    type = 'share.preprint'


class ThroughAgentWorkRelationFactory(ShareObjectFactory):
    subject = factory.SubFactory(AgentWorkRelationFactory)
    related = factory.SubFactory(AgentWorkRelationFactory)

    class Meta:
        model = models.ThroughContributor


class TagFactory(ShareObjectFactory):
    name = factory.Faker('word')

    class Meta:
        model = models.Tag


class ThroughTagsFactory(ShareObjectFactory):
    tag = factory.SubFactory(TagFactory)
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = models.ThroughTags


class WorkIdentifierFactory(ShareObjectFactory):
    scheme = 'http'
    host = 'testvalue'
    uri = factory.Faker('url')
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = models.WorkIdentifier


class AgentIdentifierFactory(ShareObjectFactory):
    scheme = 'http'
    host = 'testvalue'
    uri = factory.Faker('url')
    agent = factory.SubFactory(AgentFactory)

    class Meta:
        model = models.AgentIdentifier


class ExtraDataFactory(ShareObjectFactory):
    data = {}

    class Meta:
        model = models.ExtraData
