import copy
import logging

from django.apps import apps

from share import disambiguation


logger = logging.getLogger(__name__)


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

        return {k: v for k, v in self.attrs.items() if getattr(self.instance, k) != v}

    def __init__(self, node, disambiguate=True):
        self.__raw = node
        self.__change = None
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
    def changes(self):
        return self.__changes

    @property
    def nodes(self):
        return self.__nodes

    def __init__(self, nodes, parse=True):
        self.__parsed = False
        self.__nodes = nodes

        if parse:
            self.__parse()

    def __parse(self):
        self.__parsed = True
        to_order, self.__nodes = self.__nodes, []

        relations = {
            node: {
                (n['@id'], n['@type'])
                for n in node.relations.values()
                if not isinstance(n, (tuple, list))
            }
            for node in to_order
        }

        # Topologicallly sort graph nodes so relations can be properly built
        while to_order:
            node = to_order.pop(0)
            if relations[node]:
                to_order.append(node)
                continue
            relations.pop(node)
            self.__nodes.append(node)
            for val in relations.values():
                val.discard((node.id, node.type))
