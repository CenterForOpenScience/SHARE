import copy
import logging

from django.apps import apps

from share.disambiguation import GraphDisambiguator
from share.util import TopographicalSorter


logger = logging.getLogger(__name__)


class GraphParsingException(Exception):
    pass


class UnresolvableReference(GraphParsingException):
    pass


class ChangeNode:

    @classmethod
    def from_jsonld(self, ld_graph, extra_namespace=None):
        return ChangeNode(ld_graph, extra_namespace=extra_namespace)

    @property
    def model(self):
        if self.is_merge:
            return apps.get_model('share', self.relations['into']['@type'].lower())
        return apps.get_model('share', self.type.lower())

    @property
    def instance(self):
        return self.__instance

    @instance.setter
    def instance(self, instance):
        if instance:
            self.id = instance.pk
            self.type = instance._meta.model_name.lower()
            if self.type != self.new_type and self.new_type == 'creativework':
                self.new_type = self.type
            self.__refs.append((self.id, self.type))
        self.__instance = instance

    @property
    def is_blank(self):
        # JSON-LD Blank Node ids start with "_:"
        return self.is_merge or (isinstance(self.id, str) and self.id.startswith('_:'))

    @property
    def is_merge(self):
        return self.type.lower() == 'mergeaction'

    @property
    def ref(self):
        return {'@id': self.id, '@type': self.type}

    @property
    def refs(self):
        return self.__refs

    @property
    def is_skippable(self):
        return self.is_merge or (self.instance and not self.change)

    @property
    def resolved_attrs(self):
        return {
            **self.attrs,
            **{k: v['@id'] for k, v in self.relations.items() if not str(v['@id']).startswith('_:')},
            **{k: [x['@id'] for x in v if not str(x['@id']).startswith('_:')] for k, v in self.reverse_relations.items() if any(not str(x['@id']).startswith('_:') for x in v)},
        }

    @property
    def change(self):
        if self.is_merge:
            return {**self.attrs, **self.relations, **self.__reverse_relations}

        if self.is_blank:
            ret = {**self.attrs, **self.relations}
            if self.extra:
                ret['extra'] = self.extra
            return ret

        if not self.instance:
            raise UnresolvableReference('@id: {!r}, @type: {!r}'.format(self.id, self.type))

        ret = {k: v for k, v in self.attrs.items() if getattr(self.instance, k) != v}
        if self.__extra_namespace:
            ret['extra'] = {
                k: v for k, v in self.extra.items()
                if not (self.instance.extra and self.instance.extra.get(self.__extra_namespace))
                or self.instance.extra.data[self.__extra_namespace].get(k) != v
            }

            if not ret['extra']:
                del ret['extra']

        if self.new_type != self.type:
            ret['@type'] = self.new_type

        return ret

    def __init__(self, node, extra_namespace=None):
        self.__raw = node
        self.__change = None
        self.__instance = None
        self.__extra_namespace = None
        node = copy.deepcopy(self.__raw)

        self.id = str(node.pop('@id'))
        self.type = node.pop('@type').lower()
        self.new_type = self.type
        self.extra = node.pop('extra', {})

        self.__refs = [(self.id, self.type)]

        # JSON-LD variables are all prefixed with '@'s
        self.context = {k: node.pop(k) for k in tuple(node.keys()) if k[0] == '@'}

        # Any nested data type is a relation in the current JSON-LD schema
        self.relations = {k: node.pop(k) for k, v in tuple(node.items()) if isinstance(v, dict)}
        self.related = tuple(self.relations.values())

        self.reverse_relations = {}  # Resolved through relations to be populated later
        self.__reverse_relations = {k: tuple(node.pop(k)) for k, v in tuple(node.items()) if isinstance(v, (list, tuple))}

        self.attrs = node

    def resolve_relations(self, mapper):
        for key, relations in self.__reverse_relations.items():
            resolved = []
            for relation in relations:
                node = mapper[relation['@id'], relation['@type'].lower()]
                through_relations = [r for r in node.related if r['@id'] != self.id]
                if through_relations:
                    resolved.extend(through_relations)
                    self.related += tuple(through_relations)
                else:
                    resolved.append(node.ref)
            self.reverse_relations[key] = resolved

    def update_relations(self, mapper):
        for v in self.relations.values():
            try:
                node = mapper[(v['@id'], v['@type'].lower())]
                v['@id'] = node.id
                v['@type'] = node.new_type
            except KeyError:
                pass
        for k, values in self.reverse_relations.items():
            self.reverse_relations[k] = [mapper.get((v['@id'], v['@type'].lower()), (v['@id'], v['@type'].lower())).ref for v in values]

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.model, self.instance)


class ChangeGraph:

    @classmethod
    def from_jsonld(self, ld_graph, disambiguate=True, extra_namespace=None):
        nodes = [ChangeNode.from_jsonld(obj, extra_namespace=extra_namespace) for obj in ld_graph['@graph']]
        graph = ChangeGraph(nodes)
        if disambiguate:
            GraphDisambiguator().disambiguate(graph)
        return graph

    @property
    def nodes(self):
        return self.__nodes

    @property
    def node_map(self):
        return self.__map

    def __init__(self, nodes, parse=True):
        self.__nodes = nodes
        self.__map = {ref: n for n in nodes for ref in n.refs}
        self.__sorter = TopographicalSorter(nodes, dependencies=lambda n: [self.get_node(r['@id'], r['@type']) for r in n.related])

        for node in self.__nodes:
            node.resolve_relations(self.__map)

        if parse:
            self.__nodes = self.__sorter.sorted()

    def get_node(self, id, type):
        try:
            return self.__map[(id, type.lower())]
        except KeyError:
            if str(id).startswith('_:'):
                raise UnresolvableReference('Unresolvable reference @id: {!r}, @type: {!r}'.format(id, type))
        return None  # External reference to an already existing object
