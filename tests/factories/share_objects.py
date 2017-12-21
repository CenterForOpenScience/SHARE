import random
from datetime import timezone

import faker
import factory
from factory.django import DjangoModelFactory

from share import models

from tests.factories.changes import ChangeFactory

__all__ = (
    'AbstractAgentFactory',
    'AbstractCreativeWorkFactory',
    'AgentIdentifierFactory',
    'AgentWorkRelationFactory',
    'ExtraDataFactory',
    'TagFactory',
    'ThroughTagsFactory',
    'WorkIdentifierFactory',
    'AbstractWorkRelationFactory',
    'CreatorWorkRelationFactory',
)


faker = faker.Faker()


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


class AbstractAgentFactory(TypedShareObjectFactory):
    name = factory.Faker('company')
    given_name = factory.Faker('first_name')
    family_name = factory.Faker('last_name')

    class Meta:
        model = models.AbstractAgent


class AgentIdentifierFactory(ShareObjectFactory):
    scheme = 'http'
    host = 'testvalue'
    uri = factory.Sequence(lambda x: '{}?{}'.format(faker.uri(), x))
    agent = factory.SubFactory(AbstractAgentFactory)

    class Meta:
        model = models.AgentIdentifier


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


class WorkIdentifierFactory(ShareObjectFactory):
    scheme = 'http'
    host = 'testvalue'
    uri = factory.Sequence(lambda x: '{}?{}'.format(faker.uri(), x))
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = models.WorkIdentifier


class AgentWorkRelationFactory(TypedShareObjectFactory):
    cited_as = factory.Faker('name')
    agent = factory.SubFactory(AbstractAgentFactory)
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = models.AgentWorkRelation


class CreatorWorkRelationFactory(AgentWorkRelationFactory):
    order_cited = 0
    type = 'share.creator'

    class Meta:
        model = models.AbstractAgentWorkRelation


class TagFactory(ShareObjectFactory):
    name = factory.Sequence(lambda x: '{}{}'.format(faker.word(), x))

    class Meta:
        model = models.Tag


class ThroughTagsFactory(ShareObjectFactory):
    tag = factory.SubFactory(TagFactory)
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = models.ThroughTags


class ExtraDataFactory(ShareObjectFactory):
    data = {}

    class Meta:
        model = models.ExtraData


class AbstractWorkRelationFactory(TypedShareObjectFactory):
    subject = factory.SubFactory(AbstractCreativeWorkFactory)
    related = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = models.AbstractWorkRelation
