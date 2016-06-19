import copy
import logging

from django.utils.functional import cached_property

import share.models
from share.core.disambiguation import Disambiguator


logger = logging.getLogger(__name__)


class GraphNode:

    _MODELS = {
        'Affiliation': share.models.Affiliation,
        'Contributor': share.models.Contributor,
        'Manuscript': share.models.Manuscript,
        'Organization': share.models.Organization,
        'Person': share.models.Person,
    }

    @property
    def is_blank(self):
        return self.id.startswith('_:')

    @property
    def model(self):
        return GraphNode._MODELS[self.type]

    @cached_property
    def instance(self):
        model = Disambiguator(self.id, self.attrs, self.model).find()
        if model:
            self._found = False
            return model
        return self.model(**self.attrs)

    def __init__(self, node):
        self._raw = node
        self._found = True
        node = copy.deepcopy(self._raw)

        self.id = node.pop('@id')
        self.type = node.pop('@type')

        self._context = {k: node.pop(k) for k in tuple(node.keys()) if k[0] == '@'}
        self.relations = {k: node.pop(k) for k, v in tuple(node.items()) if isinstance(v, (dict, list, tuple))}

        self.attrs = node

    def change(self, submitter):
        if self._found:
            return share.models.ChangeRequest.objects.create_object(self.instance, submitter)
        return share.models.ChangeRequest.objects.update(self.instance, submitter)


class ChangeGraph:

    def __init__(self, ld_graph):
        self._raw = ld_graph
        self._graph = self._raw['@graph']
        self._nodes = {}
        self._relations = {}

        for obj in self._graph:
            node = GraphNode(obj)
            self._nodes[(node.id, node.type)] = node
            self._relations[node] = [x for x in node.relations.values() if not isinstance(x, (tuple, list))]

    def changes(self, submitter):
        ordered, to_order = [], list(self._nodes.values())
        relations = {k: {(n['@id'], n['@type']) for n in v} for k, v in self._relations.items()}

        while to_order:
            node = to_order.pop(0)
            if relations.get(node):
                to_order.append(node)
                continue
            relations.pop(node), ordered.append(node)
            for val in relations.values():
                val.discard((node.id, node.type))

        changes = []
        for node in ordered:
            for k, v in node.relations.items():
                if not isinstance(v, (tuple, list)):
                    setattr(node.instance, k, self._nodes[(v['@id'], v['@type'])].instance)
            changes.append(node.change(submitter))
        return changes
