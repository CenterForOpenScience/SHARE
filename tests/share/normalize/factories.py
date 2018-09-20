import contextlib
import functools
import json
import random
import re
import logging
from operator import attrgetter

import faker

import factory
import factory.fuzzy

import nameparser

from typedmodels.models import TypedModel

from django.apps import apps

from share import models
from share.transform.chain.links import IRILink
from share.util import TopologicalSorter
from share.util.graph import MutableGraph, MutableNode


logger = logging.getLogger(__name__)


used_ids = set()
_Faker = faker.Faker()


def format_id(model, id):
    id_namespace = model._meta.concrete_model._meta.model_name.lower().replace('abstract', '')
    return '_:{}--{}'.format(id_namespace, id)


class FactoryGraph(MutableGraph):
    # Override to ignore IDs
    def topologically_sorted(self):
        def sort_key(node):
            return (
                node.type,
                *(node.attrs().items())
            )

        return TopologicalSorter(
            sorted(self, key=sort_key),
            dependencies=lambda n: sorted(
                self.successors(n.id),
                key=lambda id: sort_key(self.get_node(id)),
            ),
            key=attrgetter('id'),
        ).sorted()

    # Within tests, `graph1 == graph2` compares their contents
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.to_jsonld(in_edges=False) == other.to_jsonld(in_edges=False)

    # Normalize IDs to ease comparison
    def to_jsonld(self, *args, **kwargs):
        jsonld = super().to_jsonld(*args, **kwargs)
        id_map = {
            node['@id']: '_:__{}'.format(i)
            for i, node in enumerate(jsonld)
        }

        def map_id(value):
            if isinstance(value, dict):
                value['@id'] = id_map[value['@id']]
            elif isinstance(value, list):
                for v in value:
                    map_id(v)

        for node in jsonld:
            for v in node.values():
                map_id(v)
            map_id(node)

        return jsonld

    # More readable test output
    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            json.dumps(self.to_jsonld(in_edges=False), indent=4, sort_keys=True),
        )


class FactoryNode(MutableNode):

    def __new__(cls, graph, id, type=None, **attrs):
        return super().__new__(cls, graph, id, type, attrs)

    def __init__(self, graph, id, type, **attrs):
        super().__init__(graph, id, type, attrs)


class RandomStateManager:
    def __init__(self, randoms, seed=None):
        self._randoms = randoms
        self._seed = seed or random.random()
        self._states = {}

    def get_states(self):
        return tuple(r.getstate() for r in self._randoms)

    def set_states(self, states):
        for r, state in zip(self._randoms, states):
            r.setstate(state)

    def reseed(self, seed=None):
        self._seed = seed or random.random()

        for r in self._randoms:
            r.seed(self._seed)
        # factory.fuzzy.reseed_random(self._seed)
        self._states = {}

    @contextlib.contextmanager
    def seed(self, name=None, seed=None):
        old_states = self.get_states()

        new_states = self._states.get(name) if name else None

        if new_states is None:
            initial_seed = seed or self._seed
            for r in self._randoms:
                r.seed(initial_seed)
            new_states = self.get_states()
            if name:
                self._states[name] = new_states

        self.set_states(new_states)

        yield hash(new_states)

        # Save the new state if it was advanced/used
        if name:
            self._states[name] = self.get_states()

        # Leave random(s) untouched upon exiting
        self.set_states(old_states)


class GraphBuilder:

    def __init__(self):
        self.random_states = RandomStateManager([random, _Faker.random])

    def reseed(self):
        self.random_states.reseed()

    def build(self, *nodes, normalize_fields=False):
        # Reset all seeds at the being of each graph generation
        # Ensures that graphs will be comparable
        self.random_states.reseed(self.random_states._seed)

        graph = FactoryGraph()
        NodeBuilder(graph, self.random_states, normalize_fields).build_nodes(nodes)
        return graph

    def __call__(self, *args, **kwargs):
        return self.build(*args, **kwargs)


class NodeBuilder:
    def __init__(self, graph, random_states, normalize_fields=False):
        self.graph = graph
        self.random_states = random_states
        self.normalize_fields = normalize_fields

    def get_factory(self, model):
        return globals()[model._meta.concrete_model.__name__ + 'Factory']

    def build_nodes(self, nodes):
        for n in nodes:
            if isinstance(n, list):
                self.build_nodes(n)
            else:
                self.build(n)

    def build(self, attrs):
        assert 'type' in attrs, 'Must provide "type" when constructing a node'

        attrs = {**attrs}  # make a copy to avoid mutating the arg
        node_type = attrs.pop('type')
        sparse = attrs.pop('sparse', False)
        seed = attrs.pop('seed', None)

        if 'id' in attrs and attrs['id'] in self.graph:
            id = attrs.pop('id')
            assert not attrs, 'Cannot reference a previously defined node by id and set attrs'
            return self.graph.get_node(id)

        if self.normalize_fields:
            attrs['parse'] = True

        model = apps.get_model('share', node_type)

        relations = {}
        for key in tuple(attrs.keys()):
            if isinstance(attrs[key], (dict, list)):
                relations[key] = attrs.pop(key)

        # Extract/generate required relations.
        # e.g. WorkIdentifier requires a work, Creator requires work and agent
        for f in model._meta.fields:
            if f.name not in attrs and f.is_relation and not f.null and f.editable and f.concrete:
                try:
                    relation = relations.pop(f.name)
                except KeyError:
                    # Value missing for required relation; generate a fake one
                    relation = {'type': f.remote_field.model._meta.concrete_model._meta.model_name}
                attrs[f.name] = self.build(relation)

        if sparse:
            # Don't generate fake data for missing fields
            node = FactoryNode(self.graph, type=node_type, **attrs)
        else:
            # If it's a specific type, pass it along, otherwise let the factory choose a subtype
            concrete_model_name = model._meta.concrete_model._meta.model_name
            if node_type != concrete_model_name:
                attrs['type'] = node_type

            if seed:
                seed_ctx = self.random_states.seed(seed=str(seed) + concrete_model_name)
            else:
                seed_ctx = self.random_states.seed(name=concrete_model_name)

            with seed_ctx:
                node = self.get_factory(model)(graph=self.graph, **attrs)

        # Build specified *-to-many relations
        for key, value in sorted(relations.items(), key=lambda x: x[0]):
            field = model._meta.get_field(key)

            if isinstance(value, list):
                if field.many_to_many:
                    related = [self.build(v) for v in value]
                    for rel in related:
                        self.build({
                            'type': field.remote_field.through._meta.model_name,
                            field.m2m_field_name(): node,
                            field.m2m_reverse_field_name(): rel,
                        })
                else:
                    reverse_name = field.remote_field.name
                    for v in value:
                        v[reverse_name] = node
                        self.build(v)
            else:
                node[key] = self.build(value)

        return node


class GraphNodeFactory(factory.Factory):

    id = None  # Let the graph generate an ID
    graph = factory.SelfAttribute('..graph')  # Subfactories use the parent's graph

    class Meta:
        abstract = True
        model = FactoryNode
        inline_args = ('graph',)

    @factory.lazy_attribute
    def type(stub):
        return re.sub('Factory$', '', stub._LazyStub__model_class.__name__).lower()

    @factory.post_generation
    def parse(self, _, parse, **kwargs):
        # Override this to parse fields like the regulator is expected to
        pass


class TypedGraphNodeFactory(GraphNodeFactory):

    @factory.lazy_attribute
    def type(stub):
        model_name = re.sub('Factory$', '', stub._LazyStub__model_class.__name__)
        model = apps.get_model('share', model_name)
        if issubclass(model, TypedModel) and model._meta.concrete_model is model:
            model = random.choice(model._meta.concrete_model.get_type_classes())
        return model._meta.model_name.lower()


class AbstractAgentFactory(TypedGraphNodeFactory):

    @factory.lazy_attribute
    def name(self):
        if self.type == 'person':
            if any(getattr(self, n, None) for n in ('given_name', 'family_name', 'suffix', 'additional_name')):
                return None
            return _Faker.name()
        return _Faker.company()

    class Meta:
        model = FactoryNode

    @factory.post_generation
    def parse(self, _, parse, **kwargs):
        if not parse or self.type != 'person':
            return

        name = self['name']
        if not name:
            self['name'] = ' '.join(filter(None, (
                self[k]
                for k in ['given_name', 'additional_name', 'family_name', 'suffix']
            )))
        else:
            human = nameparser.HumanName(name)
            for hk, sk in [('first', 'given_name'), ('middle', 'additional_name'), ('last', 'family_name'), ('suffix', 'suffix')]:
                if human[hk]:
                    self[sk] = human[hk]


class TagFactory(GraphNodeFactory):
    name = factory.Faker('word')


class SubjectFactory(GraphNodeFactory):
    name = factory.Faker('word')


class AbstractCreativeWorkFactory(TypedGraphNodeFactory):
    title = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    language = factory.Faker('language_code')

    # related_agents = factory.SubFactory(AgentWorkRelationFactory)

    # identifiers = factory.SubFactory('tests.share.normalize.factories.WorkIdentifierFactory')
    # related_works = factory.SubFactory(RelatedWorkFactory)
    date_updated = factory.Faker('date', pattern='%Y-%m-%dT%H:%M:%SZ')
    date_published = factory.Faker('date', pattern='%Y-%m-%dT%H:%M:%SZ')
    rights = factory.Faker('paragraph')
    free_to_read_type = factory.Faker('url')
    free_to_read_date = factory.Faker('date', pattern='%Y-%m-%dT%H:%M:%SZ')
    is_deleted = False

    class Meta:
        model = FactoryNode


class AbstractAgentWorkRelationFactory(TypedGraphNodeFactory):
    # lazy attr
    # agent = factory.SubFactory(AbstractAgentFactory)
    # creative_work = factory.SubFactory(AbstractCreativeWorkFactory)
    # order_cited = factory.Faker('pyint')

    @factory.lazy_attribute
    def cited_as(self):
        return self.agent['name']

    # lazy attr base on type
    # award = factory.SubFactory(AwardFactory)

    class Meta:
        model = FactoryNode


class AbstractWorkRelationFactory(TypedGraphNodeFactory):
    # related = factory.SubFactory(AbstractCreativeWorkFactory)
    # subject = factory.SubFactory(AbstractCreativeWorkFactory)

    class Meta:
        model = FactoryNode


class ThroughTagsFactory(GraphNodeFactory):
    pass
    # tag = factory.SubFactory(TagFactory)
    # creative_work = factory.SubFactory(AbstractCreativeWorkFactory)


class ThroughSubjectsFactory(GraphNodeFactory):
    pass
    # subject = factory.SubFactory(SubjectFactory)
    # creative_work = factory.SubFactory(AbstractCreativeWorkFactory)


class WorkIdentifierFactory(GraphNodeFactory):
    uri = factory.Faker('url')
    # creative_work = factory.SubFactory(AbstractCreativeWorkFactory)

    @factory.post_generation
    def parse(self, _, parse, **kwargs):
        if parse:
            parsed = IRILink().execute(self['uri'])
            self['uri'] = parsed['IRI']
            self['scheme'] = parsed['scheme']
            self['host'] = parsed['authority']


class AgentIdentifierFactory(GraphNodeFactory):
    uri = factory.Faker('url')
    # agent = factory.SubFactory(AbstractAgentFactory)

    @factory.post_generation
    def parse(self, _, parse, **kwargs):
        if parse:
            parsed = IRILink().execute(self['uri'])
            self['uri'] = parsed['IRI']
            self['scheme'] = parsed['scheme']
            self['host'] = parsed['authority']


def _params(seed=None, id=None, type=None, model=None, **kwargs):
    ret = {'type': type, **kwargs}
    if id is not None:
        ret['id'] = format_id(model, id)
    if seed is not None:
        ret['seed'] = seed
    return ret


__all__ = ()
for model_name in dir(models):
    model = getattr(models, model_name)
    if not hasattr(model, 'VersionModel'):
        continue
    __all__ += (model_name, )
    locals()[model_name] = functools.partial(_params, type=model_name.lower(), model=model)
