import uuid
import random
import re

import factory

from django.apps import apps


class TypedShareObjectFactory(factory.Factory):
    id = '_:' + str(uuid.uuid4())

    @factory.lazy_attribute
    def type(stub):
        model_name = re.sub('Factory$', '', stub._LazyStub__model_class.__name__)
        model = apps.get_model('share', model_name)

        return random.choice([m.model_name.lower() for m in model._meta.concrete_model._meta.proxied_children or [model._meta]])


class AgentFactory(TypedShareObjectFactory):
    name = factory.Faker('company')
    given_name = factory.Faker('first_name')
    family_name = factory.Faker('last_name')
    # affiliation = factory.SubFactory(AgentFactory)

    class Meta:
        model = dict


class WorkIdentifierFactory(factory.Factory):
    uri = factory.Faker('url')

    class Meta:
        model = dict


class AgentWorkRelationFactory(TypedShareObjectFactory):
    # lazy attr
    cited_as = factory.Faker('name')
    agent = factory.SubFactory(AgentFactory)

    # lazy attr base on type
    # creative_work = factory.SubFactory(AbstractCreativeWorkFactory)
    # award = factory.SubFactory(AwardFactory)

    class Meta:
        model = dict


class AbstractCreativeWorkFactory(TypedShareObjectFactory):
    title = factory.Faker('sentence')
    description = factory.Faker('paragraph')

    language = 'eng'
    # related_agents = factory.SubFactory(AgentWorkRelationFactory)

    subjects = []
    tags = []
    identifiers = factory.SubFactory(WorkIdentifierFactory)
    # related_works = factory.SubFactory(RelatedWorkFactory)
    date_updated = factory.Faker('date', pattern="%Y-%m-%d")
    date_published = factory.Faker('date', pattern="%Y-%m-%d")
    rights = factory.Faker('paragraph')
    free_to_read_type = factory.Faker('sentence')
    free_to_read_date = factory.Faker('date', pattern="%Y-%m-%d")
    is_deleted = False

    class Meta:
        model = dict
