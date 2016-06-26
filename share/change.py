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
        if self.type.lower() == 'mergeaction':
            return None
        return apps.get_model('share', self.type.lower())

    @property
    def instance(self):
        return self.__instance

    @property
    def is_blank(self):
        # JSON-LD Blank Node ids start with "_:"
        return isinstance(self.id, str) and self.id.startswith('_:')

    @property
    def change(self):
        if self.model is None:
            return None

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

        self.id = node.pop('@id')
        self.type = node.pop('@type')
        self.extra = node.pop('extra', {})

        # JSON-LD variables are all prefixed with '@'s
        self.context = {k: node.pop(k) for k in tuple(node.keys()) if k[0] == '@'}
        # Any nested data type is a relation in the current JSON-LD schema
        self.relations = {k: node.pop(k) for k, v in tuple(node.items()) if isinstance(v, (dict, list, tuple))}

        self.attrs = node

        if disambiguate:
            self._disambiguate()

    def _disambiguate(self):
        if not self.model:
            return None
        self.__instance = disambiguation.disambiguate(self.id, self.attrs, self.model)
        if self.__instance:
            self.id = self.__instance.pk


class ChangeGraph:

    @classmethod
    def from_jsonld(self, ld_graph, disambiguate=True):
        nodes = [ChangeNode.from_jsonld(obj, disambiguate=disambiguate) for obj in ld_graph['@graph']]
        return ChangeGraph(nodes)

    @property
    def nodes(self):
        return self.__nodes

    def __init__(self, nodes, parse=True):
        self.__nodes = nodes
        self.__map = {(n.id, n.type): n for n in nodes}
        self.__sorter = NodeSorter(self)

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
        for relation in node.relations.values():
            n = self.__graph.get_node(relation['@id'], relation['@type'])
            if n:
                self.__visit(n)

        self.__visted.add(node)
        self.__sorted.append(node)
        self.__visiting.remove(node)
