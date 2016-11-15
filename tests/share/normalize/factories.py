import pytest
import functools
import random
import re

import faker

import factory
import factory.fuzzy

from django.apps import apps

from share import models
from share.change import ChangeGraph
from share.normalize.links import IRILink


__all__ = ('Graph', )


used_ids = set()
_Faker = faker.Faker()
_remove = ChangeGraph.remove  # Intercepted method, save the original


class GraphContructor:

    def __init__(self):
        self.registry = {}
        self.discarded_ids = set()
        self._seed = random.random()

    def __call__(self, *nodes):
        self.reseed(self._seed)

        # Traverse all nodes to build proper graph
        seen, to_see = set(), [self.build_node({**n}) for n in nodes]
        while to_see:
            node = to_see.pop(0)
            if node is None:
                continue
            seen.add(node)

            for rel in list(node.related.values()) + node._related:
                if not isinstance(rel, list):
                    rel = [rel]
                for n in rel:
                    if n in seen:
                        continue
                    to_see.append(n)

        # Sort by type + id to get consitent ordering between two graphs
        return [n.serialize() for n in sorted(seen, key=lambda x: x.type + str(x.id))]

    def get_id(self):
        while True:
            id = _Faker.ipv6()
            if id not in self.discarded_ids:
                break
        return id

    def patched_remove_id(self):
        def _remove_id(this, node, cascade=True):
            self.discarded_ids.add(node._id.replace('_:', '', 1))
            return _remove(this, node, cascade=cascade)
        return _remove_id

    def reseed(self, seed=None):
        # Reset all seeds at the being of each graph generation
        # Ensures that graphs will be compairable
        self._seed = seed or random.random()

        random.seed(self._seed)
        _Faker.random.seed(self._seed)
        factory.fuzzy.reseed_random(self._seed)
        for fake in factory.Faker._FAKER_REGISTRY.values():
            fake.random.seed(self._seed)

    def get_factory(self, model):
        return globals()[model.__name__ + 'Factory']

    def build_node(self, node):
        model = apps.get_model('share', node['type'])

        relations = {}
        for key in tuple(node.keys()):
            if isinstance(node[key], (dict, list)):
                relations[key] = node.pop(key)

        if node.pop('sparse', False):
            obj = GraphNode(**node)
        else:
            # Remove type to allow random choices
            _node = {**node}
            if node['type'] == model._meta.concrete_model._meta.model_name:
                _node.pop('type', None)

            obj = self.get_factory(model._meta.concrete_model)(**_node)

        if node.get('id') is not None and (node['id'], model._meta.concrete_model) in self.registry:
            # TODO Find a better way to handle this
            # This ensures that the random generators will always be "spun" the same number of times
            # Therefore output will remain in sync
            found = self.registry[node['id'], model._meta.concrete_model]
            _node.pop('id', None)
            _node.pop('type', None)
            obj.id, obj.type, obj.attrs = found.id, found.type, {**found.attrs, **_node}

        for key, value in sorted(relations.items(), key=lambda x: x[0]):
            field = model._meta.get_field(key)
            reverse_name = field.remote_field.name

            if isinstance(value, list):
                if field.many_to_many:
                    related = [self.build_node({**v}) for v in value]
                    for rel in related:
                        obj._related.append(self.build_node({
                            'type': field.rel.through._meta.model_name,
                            field.m2m_field_name(): obj,
                            field.m2m_reverse_field_name(): rel,
                        }))
                else:
                    obj._related.append([self.build_node({**v, reverse_name: obj}) for v in value])
            else:
                args = {**value}
                if not field.concrete:
                    args[field.remote_field.name] = obj

                obj.related[key] = self.build_node(args)

        if len(obj.id) < 20:
            self.registry[obj.id, model._meta.concrete_model] = obj

        return obj


@pytest.fixture
def Graph(monkeypatch):
    c = GraphContructor()
    ShareObjectFactory._meta.declarations['id'].function = lambda: '_:' + c.get_id()
    monkeypatch.setattr('share.change.uuid.uuid4', c.get_id)
    monkeypatch.setattr('share.change.ChangeGraph.remove', c.patched_remove_id())
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
        self._related = []
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


class AbstractAgentFactory(TypedShareObjectFactory):

    @factory.lazy_attribute
    def name(self):
        if self.type == 'person':
            if any(getattr(self, n, None) for n in ('given_name', 'family_name', 'suffix', 'additional_name')):
                return None
            return _Faker.name()
        return _Faker.company()

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


class AbstractAgentWorkRelationFactory(TypedShareObjectFactory):
    # lazy attr
    @factory.lazy_attribute
    def cited_as(self):
        return self.agent.attrs['name']
    agent = factory.SubFactory(AbstractAgentFactory)
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    # lazy attr base on type
    # award = factory.SubFactory(AwardFactory)

    class Meta:
        model = GraphNode


class AbstractWorkRelationFactory(TypedShareObjectFactory):
    subject = factory.SubFactory(AbstractCreativeWorkFactory)
    related = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = GraphNode


class ThroughTagsFactory(ShareObjectFactory):
    tag = factory.SubFactory(TagFactory)
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)


class WorkIdentifierFactory(ShareObjectFactory):
    uri = factory.Faker('url')
    creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    @factory.lazy_attribute
    def scheme(self):
        if not self.parse:
            return None
        return IRILink().execute(self.uri)['scheme']

    @factory.lazy_attribute
    def host(self):
        if not self.parse:
            return None
        return IRILink().execute(self.uri)['authority']

    class Params:
        parse = False


class AgentIdentifierFactory(ShareObjectFactory):
    uri = factory.Faker('url')
    agent = factory.SubFactory(AbstractAgentFactory)

    @factory.lazy_attribute
    def scheme(self):
        if not self.parse:
            return None
        return IRILink().execute(self.uri)['scheme']

    @factory.lazy_attribute
    def host(self):
        if not self.parse:
            return None
        return IRILink().execute(self.uri)['authority']

    class Params:
        parse = False


def _params(id=None, type=None, **kwargs):
    string_id = '_:' + str(id)
    ret = {'id': string_id, 'type': type, **kwargs}
    if id is None:
        ret.pop('id')
    return ret

for model in dir(models):
    if not hasattr(getattr(models, model), 'VersionModel'):
        continue
    __all__ += (model, )
    locals()[model] = functools.partial(_params, type=model.lower())
