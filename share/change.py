import copy
import logging

from django.apps import apps

from share import disambiguation


logger = logging.getLogger(__name__)


class GraphParsingException(Exception):
    pass


class CyclicalDependency(GraphParsingException):
    pass


class UnresolvableReference(GraphParsingException):
    pass


class ChangeNode:

    @classmethod
    def from_jsonld(self, ld_graph, disambiguate=True):
        return ChangeNode(ld_graph, disambiguate=disambiguate)

    @property
    def model(self):
        if self.is_merge:
            return apps.get_model('share', self.relations['into']['@type'].lower())
        return apps.get_model('share', self.type.lower())

    @property
    def instance(self):
        return self.__instance

    @property
    def is_blank(self):
        # JSON-LD Blank Node ids start with "_:"
        return self.is_merge or (isinstance(self.id, str) and self.id.startswith('_:'))

    @property
    def is_merge(self):
        return self.type.lower() == 'mergeaction'

    @property
    def refs(self):
        return self.__refs

    @property
    def change(self):
        if self.is_merge:
            return {**self.attrs, **self.relations, **self._reverse_relations}

        if self.is_blank:
            return {**self.attrs, **self.relations}

        if not self.instance:
            raise UnresolvableReference('@id: {!r}, @type: {!r}'.format(self.id, self.type))

        return {k: v for k, v in self.attrs.items() if getattr(self.instance, k) != v}

    def __init__(self, node, disambiguate=True):
        self.__raw = node
        self.__change = None
        self.__instance = None
        node = copy.deepcopy(self.__raw)

        self.id = str(node.pop('@id'))
        self.type = node.pop('@type').lower()
        self.extra = node.pop('extra', {})

        self.__refs = [(self.id, self.type)]

        # JSON-LD variables are all prefixed with '@'s
        self.context = {k: node.pop(k) for k in tuple(node.keys()) if k[0] == '@'}
        # Any nested data type is a relation in the current JSON-LD schema
        self.relations = {k: node.pop(k) for k, v in tuple(node.items()) if isinstance(v, dict)}
        self.related = tuple(self.relations.values())
        self._reverse_relations = {k: tuple(node.pop(k)) for k, v in tuple(node.items()) if isinstance(v, (list, tuple))}

        if self.is_merge:
            self.related += sum(self._reverse_relations.values(), tuple())

        self.attrs = node

        if disambiguate:
            self._disambiguate()

    def update_relations(self, mapper):
        for v in self.relations.values():
            node = mapper[(v['@id'], v['@type'])]
            if node:
                v['@id'] = node.id
                v['@type'] = node.type

    def _disambiguate(self):
        if self.is_merge:
            return None
        self.__instance = disambiguation.disambiguate(self.id, {
            **self.attrs,
            **{k: v['@id'] for k, v in self.relations.items() if not str(v['@id']).startswith('_:')}
        }, self.model)
        if self.__instance:
            self.id = self.__instance.pk
            self.__refs.append((self.id, self.type))


class ChangeGraph:

    @classmethod
    def from_jsonld(self, ld_graph, disambiguate=True):
        nodes = [ChangeNode.from_jsonld(obj, disambiguate=disambiguate) for obj in ld_graph['@graph']]
        return ChangeGraph(nodes, disambiguate=disambiguate)

    @property
    def nodes(self):
        return self.__nodes

    def __init__(self, nodes, parse=True, disambiguate=True):
        self.__nodes = nodes
        self.__map = {ref: n for n in nodes for ref in n.refs}
        self.__sorter = NodeSorter(self)

        # TODO This could probably be more efficiant
        if disambiguate:
            for n in self.__nodes:
                n.update_relations(self.__map)
            for n in self.__nodes:
                n._disambiguate()

        if parse:
            self.__nodes = self.__sorter.sorted()

    def get_node(self, id, type):
        try:
            return self.__map[(id, type)]
        except KeyError:
            if str(id).startswith('_:'):
                raise UnresolvableReference('Unresolvable reference @id: {!r}, @type: {!r}'.format(id, type))
        return None  # External reference to an already existing object


class NodeSorter:

    def __init__(self, graph):
        self.__sorted = []
        self.__graph = graph
        self.__visted = set()
        self.__visiting = set()
        self.__nodes = list(graph.nodes)

    def sorted(self):
        if not self.__nodes:
            return self.__sorted

        while self.__nodes:
            n = self.__nodes.pop(0)
            self.__visit(n)

        return self.__sorted

    def __visit(self, node):
        if node in self.__visiting:
            raise CyclicalDependency()

        if node in self.__visted:
            return

        self.__visiting.add(node)
        for relation in node.related:
            n = self.__graph.get_node(relation['@id'], relation['@type'])
            if n:
                self.__visit(n)

        self.__visted.add(node)
        self.__sorted.append(node)
        self.__visiting.remove(node)
