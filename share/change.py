import uuid
import copy
import logging
import pendulum
import datetime

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist

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
    def remote_field(self):
        return self.field.remote_field

    @property
    def name(self):
        return self.field.name

    @property
    def remote_name(self):
        return self.remote_field.name

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

    def __init__(self, data, namespace=None):
        self.nodes = []
        self.relations = {}
        self._lookup = {}
        self.namespace = namespace

        hints, relations = {}, set()
        for blob in copy.deepcopy(data):
            id, type = blob.pop('@id'), blob.pop('@type').lower()

            self._lookup[id, type] = ChangeNode(self, id, type, blob, namespace=namespace)
            self.relations[self._lookup[id, type]] = set()
            self.nodes.append(self._lookup[id, type])

            for k, v in tuple(blob.items()):
                if isinstance(v, dict) and k != 'extra' and not k.startswith('@'):
                    related = (v.pop('@id'), v.pop('@type').lower())
                    hints[(id, type), related] = k
                    relations.add(((id, type), related))
                    blob.pop(k)
                if isinstance(v, list):
                    for rel in v:
                        subject = (rel.pop('@id'), rel.pop('@type').lower())
                        relations.add((subject, (id, type)))
                    blob.pop(k)

        for subject, related in relations:
            try:
                edge = GraphEdge(self._lookup[subject], self._lookup[related], hint=hints.get((subject, related)))
            except KeyError as e:
                raise UnresolvableReference(*e.args)

            self.relations[self._lookup[subject]].add(edge)
            self.relations[self._lookup[related]].add(edge)

        self.nodes = TopographicalSorter(self.nodes, dependencies=lambda n: tuple(e.related for e in n.related(backward=False))).sorted()

    def prune(self):
        gd = GraphDisambiguator()
        gd.prune(self)
        self.nodes = TopographicalSorter(self.nodes, dependencies=lambda n: tuple(e.related for e in n.related(backward=False))).sorted()

    def disambiguate(self):
        gd = GraphDisambiguator()
        gd.find_instances(self)
        self.nodes = TopographicalSorter(self.nodes, dependencies=lambda n: tuple(e.related for e in n.related(backward=False))).sorted()

    def normalize(self):
        # Freeze nodes to avoid oddities with inserting and removing nodes
        for node in tuple(self.nodes):
            # If a node has been removed dont normalize it
            # Fast check may be wrong if type has changed double check with a slower method
            if not (node.id, node.type) in self._lookup and node not in self.nodes:
                logger.debug('Skipping removed node %s', node)
                continue
            # This feels overly hacky
            if hasattr(node.model, 'normalize'):
                node.model.normalize(node, self)

    def process(self, normalize=True, prune=True, disambiguate=True):
        if normalize:
            self.normalize()

        gd = GraphDisambiguator()

        if prune:
            gd.prune(self)

        if disambiguate:
            gd.find_instances(self)

        self.nodes = TopographicalSorter(self.nodes, dependencies=lambda n: tuple(e.related for e in n.related(backward=False))).sorted()

    def get(self, id, type):
        return self._lookup[(id, type)]

    def create(self, id, type, attrs):
        return self.add(ChangeNode(self, id or '_:{}'.format(uuid.uuid4()), type, attrs, namespace=self.namespace))

    def add(self, node):
        node.graph = self
        self.nodes.append(node)
        self.relations[node] = set()
        self._lookup[node.id, node.type] = node
        return node

    def relate(self, subject, related, hint=None):
        edge = GraphEdge(subject, related, hint)
        self.relations[subject].add(edge)
        self.relations[related].add(edge)
        return edge

    def replace(self, source, replacement):
        for edge in tuple(source.related()):
            # NOTE: Order of add & removes matters here due to
            # the hash function of an edge and how sets work
            self.relations[source].remove(edge)
            if edge.subject == source:
                self.relations[edge.related].remove(edge)
                edge.subject = replacement
                self.relations[edge.related].add(edge)
            else:
                self.relations[edge.subject].remove(edge)
                edge.related = replacement
                self.relations[edge.subject].add(edge)
            self.relations[replacement].add(edge)

        return self.remove(source)

    def remove(self, node, cascade=True):
        for edge in tuple(self.relations[node]):
            if edge.subject is node:
                self.relations[edge.related].remove(edge)
            elif cascade:
                self.remove(edge.subject, cascade=True)
            else:
                self.relations[edge.subject].remove(edge)

        self.nodes.remove(node)
        del self.relations[node]
        try:
            del self._lookup[node.id, node.type]
        except KeyError:
            key = next(k for k in self._lookup.keys() if k[0] == node.id)
            logger.warning('Could not find lookup entry for %s. Falling back to %s', node, key)
            del self._lookup[key]

    def serialize(self):
        return [
            n.serialize()
            for n in sorted(self.nodes, key=lambda x: x.type + str(x.id))
        ]


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
        model = apps.get_model('share', self._type)
        if not self.instance or len(model.mro()) >= len(type(self.instance).mro()):
            return model
        # Special case to allow creators to be downgraded to contributors
        # This allows OSF users to mark project contributors as bibiliographic or non-bibiliographic
        # and have that be reflected in SHARE
        if issubclass(model, apps.get_model('share', 'contributor')):
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

        extra = copy.deepcopy(self.extra)
        if self.namespace:
            if self.namespace and getattr(self.instance, 'extra', None):
                # NOTE extra changes are only diffed at the top level
                self.instance.extra.data.setdefault(self.namespace, {})
                changes['extra'] = {
                    k: v
                    for k, v in extra.items()
                    if k not in self.instance.extra.data[self.namespace]
                    or self.instance.extra.data[self.namespace][k] != v
                }
            else:
                changes['extra'] = extra
            if not changes['extra']:
                del changes['extra']

        for edge in self.related(backward=False):
            if edge.field.one_to_many:
                relations.setdefault(edge.name, []).append(edge.related.ref)
            else:
                relations[edge.name] = edge.related.ref

        if self.is_blank:
            return {**changes, **self.attrs, **relations}

        if self.instance and type(self.instance) is not self.model:
            changes['type'] = self.model._meta.label_lower

        # Hacky fix for SHARE-604
        # If the given date_updated is older than the current one, don't accept any changes that would overwrite newer changes
        ignore_attrs = set()
        if issubclass(self.model, apps.get_model('share', 'creativework')) and 'date_updated' in self.attrs and self.instance.date_updated:
            date_updated = pendulum.parse(self.attrs['date_updated'])
            if date_updated < self.instance.date_updated:
                logger.warning('%s appears to be from the past, change date_updated (%s) is older than the current (%s). Ignoring conflicting changes.', self, self.attrs['date_updated'], self.instance.date_updated)
                # Just in case
                ignore_attrs.update(self.instance.change.change.keys())

                # Go back until we find a change that is older than us
                for version in self.instance.versions.select_related('change').all():
                    if not version.date_updated or date_updated > version.date_updated:
                        break
                    ignore_attrs.update(version.change.change.keys())

        attrs = {}
        for k, v in self.attrs.items():
            if k in ignore_attrs:
                logger.debug('Ignoring potentially conflicting change to "%s"', k)
                continue
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
        self.namespace = namespace

        if not self.is_blank:
            self.instance = IDObfuscator.load(self.id, None)
            if not self.instance or self.instance._meta.concrete_model is not self.model._meta.concrete_model:
                raise UnresolvableReference((self.id, self.type))

    def related(self, name=None, forward=True, backward=True):
        edges = tuple(
            e for e in self.graph.relations[self]
            if (forward is True and e.subject is self and (name is None or e.name == name))
            or (backward is True and e.related is self and (name is None or e.remote_name == name))
        )

        if not name:
            return edges

        try:
            if getattr(self.model._meta.get_field(name), 'multiple', False):
                return edges
        except FieldDoesNotExist:
            return None

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

    def serialize(self):
        relations = {}
        for edge in self.related(backward=False):
            if edge.field.one_to_many:
                relations.setdefault(edge.name, []).append(edge.related.ref)
            else:
                relations[edge.name] = edge.related.ref

        return {**self.ref, **self.attrs, **relations}

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.id, self.type)
