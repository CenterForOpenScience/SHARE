import copy
import logging
import pendulum
import datetime

from django.apps import apps

from share.disambiguation import GraphDisambiguator
from share.util import TopographicalSorter
from share.util import IDObfuscator


logger = logging.getLogger(__name__)


class GraphParsingException(Exception):
    pass


class UnresolvableReference(GraphParsingException):
    pass


class GraphEdge:

    # TODO Cache
    @property
    def field(self):
        subject_model = self.subject.model
        related_model = self.related.model._meta.concrete_model
        possible = tuple(
            f for f in subject_model._meta.get_fields()
            if f.is_relation
            and f.related_model is related_model
            and (not self._hint or f.name == self._hint)
        )
        assert len(possible) == 1

        return possible[0]

    @property
    def name(self):
        return self.field.name

    @property
    def remote_name(self):
        return self.field.remote_field.name

    def __init__(self, subject, related, hint=None):
        self.subject = subject
        self.related = related
        self._hint = hint

    def __eq__(self, other):
        return type(self) is type(other) and self.related == other.related and self.subject == other.subject

    def __hash__(self):
        return hash((self.subject, self.related))

    def __repr__(self):
        return '<{}({}, {}, {})>'.format(self.__class__.__name__, self.name, self.subject, self.related)


class ChangeGraph:

    def __init__(self, data, disambiguate=True, namespace=None):
        self.nodes = []
        self.relations = {}
        self._lookup = {}

        hints, relations = {}, set()
        for blob in copy.deepcopy(data):
            id, type = blob.pop('@id'), blob.pop('@type')

            self._lookup[id, type] = ChangeNode(self, id, type, blob, namespace=namespace)
            self.relations[self._lookup[id, type]] = set()
            self.nodes.append(self._lookup[id, type])

            for k, v in tuple(blob.items()):
                if isinstance(v, dict) and k != 'extra' and not k.startswith('@'):
                    related = (v.pop('@id'), v.pop('@type'))
                    hints[(id, type), related] = k
                    relations.add(((id, type), related))
                    blob.pop(k)
                if isinstance(v, list):
                    for rel in v:
                        subject = (rel.pop('@id'), rel.pop('@type'))
                        relations.add((subject, (id, type)))
                    blob.pop(k)

        for subject, related in relations:
            try:
                edge = GraphEdge(self._lookup[subject], self._lookup[related], hint=hints.get((subject, related)))
            except KeyError as e:
                raise UnresolvableReference(*e.args)

            self.relations[self._lookup[subject]].add(edge)
            self.relations[self._lookup[related]].add(edge)

        if disambiguate:
            self.disambiguate()

        self.nodes = TopographicalSorter(self.nodes, dependencies=lambda n: tuple(e.related for e in n.related(backward=False))).sorted()

    def disambiguate(self):
        GraphDisambiguator().disambiguate(self)
        self.nodes = TopographicalSorter(self.nodes, dependencies=lambda n: tuple(e.related for e in n.related(backward=False))).sorted()

    def replace(self, source, replacement):
        self.nodes.remove(source)
        for edge in self.relations.pop(source):
            if edge.subject == source:
                self.relations[replacement].add(GraphEdge(replacement, edge.related, edge._hint))
                continue
            self.relations[edge.subject].remove(edge)
            self.relations[edge.subject].add(GraphEdge(edge.subject, replacement, edge._hint))


class ChangeNode:

    @property
    def id(self):
        return (self.instance and IDObfuscator.encode(self.instance)) or self._id

    @property
    def type(self):
        model = apps.get_app_config('share').get_model(self._type)
        if not self.instance or len(model.mro()) >= len(type(self.instance).mro()):
            return self._type
        return self.instance._meta.model_name.lower()

    @property
    def ref(self):
        return {'@id': self.id, '@type': self.type}

    @property
    def model(self):
        model = apps.get_app_config('share').get_model(self._type)
        if not self.instance or len(model.mro()) >= len(type(self.instance).mro()):
            return model
        return type(self.instance)

    @property
    def is_merge(self):
        return False  # TODO

    @property
    def is_blank(self):
        return self.id.startswith('_:')

    @property
    def is_skippable(self):
        return self.is_merge or (self.instance and not self.change)

    @property
    def change(self):
        changes, relations = {}, {}

        if self._namespace:
            extra = ((getattr(self.instance, 'extra', None)and self.instance.extra.data) or {}).get(self._namespace, {})
            changes['extra'] = {k: v for k, v in self.extra.items() if extra.get(k) != v}
            if not changes['extra']:
                del changes['extra']

        for edge in self.related(backward=False):
            if edge.field.one_to_many:
                relations.setdefault(edge.name, []).append(edge.related.ref)
            else:
                relations[edge.name] = edge.related.ref

        if self.is_blank:
            return {**self.attrs, **relations}

        if self.instance and type(self.instance) is not self.model:
            changes['type'] = self.model._meta.label_lower

        attrs = {}
        for k, v in self.attrs.items():
            old_value = getattr(self.instance, k)
            if isinstance(old_value, datetime.datetime):
                v = pendulum.parse(v)
            if v != old_value:
                attrs[k] = v.isoformat() if isinstance(v, datetime.datetime) else v

        # TODO Add relationships in. Somehow got ommitted first time around
        return {**changes, **attrs}

    def __init__(self, graph, id, type, attrs, namespace=None):
        self.graph = graph
        self._id = id
        self._type = type.lower()
        self.instance = None
        self.attrs = attrs
        self.extra = attrs.pop('extra', {})
        self.context = attrs.pop('@context', {})
        self._namespace = namespace

        if not self.is_blank:
            self.instance = IDObfuscator.load(self.id, None)
            if not self.instance or self.instance._meta.concrete_model is not self.model._meta.concrete_model:
                raise UnresolvableReference((self.id, self.type))

    def related(self, name=None, many=False, forward=True, backward=True):
        edges = tuple(
            e for e in self.graph.relations[self]
            if (name is None or e.name == name)
            and (
                (e.subject is self and forward is True)
                or (e.related is self and backward is True)
            ))

        if name is None or many:
            return edges

        assert len(edges) < 2
        return (edges and edges[0]) or None

    def resolve_attrs(self):
        relations = {}
        for edge in self.related():
            name = edge.name if edge.subject == self else edge.remote_name
            node = edge.related if edge.subject == self else edge.subject
            many = edge.field.one_to_many if edge.subject == self else edge.field.remote_field.one_to_many
            if not node.instance:
                continue
            if many:
                relations.setdefault(name, []).append(node.instance.pk)
            else:
                relations[name] = node.instance.pk

        return {**self.attrs, **relations}

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.id, self.type)
