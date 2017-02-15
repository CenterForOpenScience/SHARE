import contextlib
import functools
import inspect
import pytest
import random
import re
import logging

import faker

import factory
import factory.fuzzy

import nameparser

from django.apps import apps

from share import models
from share.change import ChangeGraph
from share.normalize.links import IRILink


__all__ = ('Graph', )
logger = logging.getLogger(__name__)


used_ids = set()
_Faker = faker.Faker()
_remove = ChangeGraph.remove  # Intercepted method, save the original


class GraphContructor:

    def __init__(self):
        self._seed = random.random()
        self._states = {}
        self.discarded_ids = set()

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

    @contextlib.contextmanager
    def seed(self, name=None, seed=None):
        old_state = (random.getstate(), _Faker.random.getstate())

        if name not in self._states:
            logger.warning('No state for %s. Seeding with %s', name, seed or self._seed)
            random.seed(seed or self._seed)
            _Faker.random.seed(seed or self._seed)
            self._states[name] = (random.getstate(), _Faker.random.getstate())

        random.setstate(self._states[name][0])
        _Faker.random.setstate(self._states[name][1])

        yield hash(self._states[name])

        # Save the new state if it was advanced/used
        self._states[name] = (random.getstate(), _Faker.random.getstate())
        if not name:
            del self._states[name]
        else:
            logger.info('Saving state %s for %s.', hash(self._states[name]), name)

        # Leave random(s) untouched upon exitting
        random.setstate(old_state[0])
        _Faker.random.setstate(old_state[1])

    def get_id(self):
        # Crazy bad hack
        # Reach up the stack until we find the type of object
        # that is requesting an ID
        # This way order only matters for an individual object.
        try:
            name = inspect.stack(3)[2].frame.f_locals['obj'].type
        except KeyError:
            name = inspect.stack(2)[1].frame.f_locals['type']

        name = apps.get_model('share', name)._meta.concrete_model._meta.model_name

        with self.seed(name + ' ids', seed=name + ' ids'):
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

        # random.seed(self._seed)
        # _Faker.random.seed(self._seed)
        factory.fuzzy.reseed_random(self._seed)
        self._states = {}

    def get_factory(self, model):
        return globals()[model.__name__ + 'Factory']

    def build_node(self, node):
        model = apps.get_model('share', node['type'])
        logger.debug('Building %s for node %s', model, node)

        relations = {}
        for key in tuple(node.keys()):
            if isinstance(node[key], (dict, list)):
                relations[key] = node.pop(key)

        for f in model._meta.fields:
            if not (f.is_relation and not f.null and f.editable and f.concrete) or f.name in node:
                continue
            if f.name not in relations:
                logger.warning('Found missing required field %s. Inserting default', f)
                relations[f.name] = {'type': f.rel.model._meta.concrete_model._meta.model_name}
            node[f.name] = self.build_node({**relations.pop(f.name)})

        kwargs = {}
        if node.get('seed'):
            kwargs['seed'] = str(node.get('seed')) + model._meta.concrete_model._meta.model_name
        else:
            kwargs['name'] = model._meta.concrete_model

        if node.pop('sparse', False):
            obj = GraphNode(**node)
        else:
            _node = {**node}
            _node.pop('seed', None)
            if node['type'] == model._meta.concrete_model._meta.model_name:
                _node.pop('type', None)

            with self.seed(**kwargs):
                obj = self.get_factory(model._meta.concrete_model)(**_node)

        logger.debug('Built %s, %s, %s for node %s', obj.id, obj.type, obj.attrs, node)

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

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash((self.id, self.type))


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
    parse = False

    @factory.lazy_attribute
    def name(self):
        if self.type == 'person':
            if any(getattr(self, n, None) for n in ('given_name', 'family_name', 'suffix', 'additional_name')):
                return None
            return _Faker.name()
        return _Faker.company()

    class Meta:
        model = GraphNode

    @factory.post_generation
    def _parse(self, *args, **kwargs):
        if not self.attrs.pop('parse') or self.type != 'person':
            return
        if not self.attrs.get('name'):
            self.attrs['name'] = ' '.join(self.attrs[k] for k in ['given_name', 'additional_name', 'family_name', 'suffix'] if self.attrs.get(k))
        else:
            human = nameparser.HumanName(self.attrs['name'])
            for hk, sk in [('first', 'given_name'), ('middle', 'additional_name'), ('last', 'family_name'), ('suffix', 'suffix')]:
                if human[hk]:
                    self.attrs[sk] = human[hk]


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
    # agent = factory.SubFactory(AbstractAgentFactory)
    # creative_work = factory.SubFactory(AbstractCreativeWorkFactory)
    # order_cited = factory.Faker('pyint')

    @factory.lazy_attribute
    def cited_as(self):
        return self.agent.attrs['name']

    # lazy attr base on type
    # award = factory.SubFactory(AwardFactory)

    class Meta:
        model = GraphNode


class AbstractWorkRelationFactory(TypedShareObjectFactory):
    # related = factory.SubFactory(AbstractCreativeWorkFactory)
    # subject = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = GraphNode


class ThroughTagsFactory(ShareObjectFactory):
    pass
    # tag = factory.SubFactory(TagFactory)
    # creative_work = factory.SubFactory(AbstractCreativeWorkFactory)


class WorkIdentifierFactory(ShareObjectFactory):
    parse = False
    uri = factory.Faker('url')
    # creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    @factory.post_generation
    def _parse(self, *args, **kwargs):
        if self.attrs.pop('parse'):
            parsed = IRILink().execute(self.attrs['uri'])
            self.attrs['scheme'] = parsed['scheme']
            self.attrs['host'] = parsed['authority']


class AgentIdentifierFactory(ShareObjectFactory):
    parse = False
    uri = factory.Faker('url')
    # agent = factory.SubFactory(AbstractAgentFactory)

    @factory.post_generation
    def _parse(self, *args, **kwargs):
        if self.attrs.pop('parse'):
            parsed = IRILink().execute(self.attrs['uri'])
            self.attrs['scheme'] = parsed['scheme']
            self.attrs['host'] = parsed['authority']


def _params(seed=None, id=None, type=None, **kwargs):
    string_id = id if isinstance(id, str) else '_:_' + str(id)
    ret = {'id': string_id, 'type': type, **kwargs}
    if id is None:
        ret.pop('id')
    if seed is not None:
        ret['seed'] = seed
    return ret

for model in dir(models):
    if not hasattr(getattr(models, model), 'VersionModel'):
        continue
    __all__ += (model, )
    locals()[model] = functools.partial(_params, type=model.lower())
