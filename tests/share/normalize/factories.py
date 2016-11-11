import pytest
import functools
import random
import re

import faker

import factory
import factory.fuzzy

from django.apps import apps

from share import models


__all__ = ('Graph', )

_Faker = faker.Faker()


class GraphContructor:

    def __init__(self):
        self.registry = {}
        self._seed = random.random()

    def __call__(self, *nodes):
        # Reset all seeds at the being of each graph generation
        # Ensures that graphs will be compairable
        random.seed(self._seed)
        _Faker.random.seed(self._seed)
        factory.fuzzy.reseed_random(self._seed)
        for fake in factory.Faker._FAKER_REGISTRY.values():
            fake.random.seed(self._seed)

        # Traverse all nodes to build proper graph
        seen, to_see = set(), [self.build_node(n) for n in nodes]
        while to_see:
            node = to_see.pop(0)
            seen.add(node)

            for rel in node.related.values():
                if not isinstance(rel, list):
                    rel = [rel]
                for n in rel:
                    if n in seen:
                        continue
                    to_see.append(n)

        # Sort by type + id to get consitent ordering between two graphs
        return [n.serialize() for n in sorted(seen, key=lambda x: x.type + str(x.id))]

    def get_factory(self, model):
        return globals()[model.__name__ + 'Factory']

    def build_node(self, node):
        model = apps.get_model('share', node['type'])

        if node.get('id') is not None and (node['id'], model._meta.concrete_model) in self.registry:
            return self.registry[node['id'], model._meta.concrete_model]

        relations = {}

        for key in tuple(node.keys()):
            if isinstance(node[key], (dict, list)):
                relations[key] = node.pop(key)

        obj = self.get_factory(model._meta.concrete_model)(**node)

        for key, value in relations.items():
            field = model._meta.get_field(key)
            reverse_name = field.remote_field.name

            if isinstance(value, list):
                if field.many_to_many:
                    related = [self.build_node(v) for v in value]
                    obj.related[field.name] = [
                        self.build_node({
                            'type': field.rel.through._meta.model_name,
                            field.m2m_field_name(): obj,
                            field.m2m_reverse_field_name(): rel,
                        })
                        for rel in related
                    ]
                else:
                    obj.related[key] = [self.build_node({**v, reverse_name: obj}) for v in value]
            else:
                obj.related[key] = self.build_node({
                    **value,
                    model._meta.get_field(key).remote_field.name: obj
                })

        self.registry[obj.id, model._meta.concrete_model] = obj

        return obj


@pytest.fixture
def Graph():
    c = GraphContructor()
    return c


class GraphNode:

    @property
    def ref(self):
        return {'@id': self.id, '@type': self.type}

    def __init__(self, **kwargs):
        self.id = kwargs.pop('id')
        self.type = kwargs.pop('type')
        self.attrs = kwargs
        self.related = {}
        self._serialized = None

        for key in tuple(self.attrs.keys()):
            if isinstance(self.attrs[key], (GraphNode, list)):
                self.related[key] = self.attrs.pop(key)

    def serialize(self):
        if self._serialized:
            return self._serialized

        self._serialized = {
            k: v for k, v in {
                **self.ref,
                **self.attrs,
                **{k: [n.ref for n in v] if isinstance(v, list) else v.ref for k, v in self.related.items()}
            }.items() if v not in (None, [])
        }
        return self._serialized


class ShareObjectFactory(factory.Factory):

    id = factory.LazyFunction(lambda: '_:' + _Faker.ipv6())

    class Meta:
        abstract = True
        model = GraphNode

    @factory.lazy_attribute
    def type(stub):
        return re.sub('Factory$', '', stub._LazyStub__model_class.__name__).lower()


class TypedShareObjectFactory(ShareObjectFactory):

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
        model = GraphNode


class WorkIdentifierFactory(ShareObjectFactory):
    uri = factory.Faker('url')


class AgentWorkRelationFactory(TypedShareObjectFactory):
    # lazy attr
    cited_as = factory.Faker('name')
    agent = factory.SubFactory(AgentFactory)

    # lazy attr base on type
    # creative_work = factory.SubFactory(AbstractCreativeWorkFactory)
    # award = factory.SubFactory(AwardFactory)

    class Meta:
        model = GraphNode


class TagFactory(ShareObjectFactory):
    name = factory.Faker('word')


class AbstractCreativeWorkFactory(TypedShareObjectFactory):
    title = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    language = factory.Faker('language_code')

    # related_agents = factory.SubFactory(AgentWorkRelationFactory)

    # identifiers = factory.SubFactory(WorkIdentifierFactory)
    # related_works = factory.SubFactory(RelatedWorkFactory)
    date_updated = factory.Faker('date', pattern="%Y-%m-%d")
    date_published = factory.Faker('date', pattern="%Y-%m-%d")
    rights = factory.Faker('paragraph')
    free_to_read_type = factory.Faker('sentence')
    free_to_read_date = factory.Faker('date', pattern="%Y-%m-%d")
    is_deleted = False

    class Meta:
        model = GraphNode


class ThroughTagsFactory(ShareObjectFactory):
    tag = factory.SubFactory(TagFactory)
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)


def _params(id=None, type=None, **kwargs):
    ret = {'id': id, 'type': type, **kwargs}
    if id is None:
        ret.pop('id')
    return ret

for model in dir(models):
    if not hasattr(getattr(models, model), 'VersionModel'):
        continue
    __all__ += (model, )
    locals()[model] = functools.partial(_params, type=model.lower())
