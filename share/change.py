import copy
import logging

from django.utils.functional import cached_property

import share.models
import share.models.creative.contributors
from share.disambiguation import disambiguate


logger = logging.getLogger(__name__)


class GraphNode:

    _MODELS = {
        'affiliation': share.models.Affiliation,
        'contributor': share.models.creative.contributors.Contributor,
        'manuscript': share.models.Manuscript,
        'organization': share.models.Organization,
        'person': share.models.Person,
    }

    @property
    def is_blank(self):
        # JSON-LD Blank Node ids start with "_:"
        return isinstance(self.id, str) and self.id.startswith('_:')

    @property
    def model(self):
        return GraphNode._MODELS[self.type.lower()]

    @cached_property
    def instance(self):
        model = disambiguate(self.id, self.attrs, self.model)
        if model:
            self._found = True
            return model
        return self.model(**self.attrs)

    def __init__(self, node):
        self._raw = node
        self._found = False
        node = copy.deepcopy(self._raw)

        self.id = node.pop('@id')
        self.type = node.pop('@type')

        # JSON-LD variables are all prefixed with '@'s
        self._context = {k: node.pop(k) for k in tuple(node.keys()) if k[0] == '@'}
        # Any nested data type is a relation in the current JSON-LD schema
        self.relations = {k: node.pop(k) for k, v in tuple(node.items()) if isinstance(v, (dict, list, tuple))}

        self.attrs = node

    def change(self, change_set):
        self.instance  # noqa
        if self._found:
            return share.models.ChangeRequest.objects.update_object(self.instance, change_set)
        return share.models.ChangeRequest.objects.create_object(self.instance, change_set)


class ChangeGraph:

    def __init__(self, ld_graph):
        self._raw = ld_graph
        self._graph = self._raw['@graph']
        self._nodes = {}
        self._relations = {}
        self.__changes = None
        self.__change_set = None

        for obj in self._graph:
            node = GraphNode(obj)
            self._nodes[(node.id, node.type)] = node
            # NOTE: lists and tuples are ignored here as many to many|one relations are handled by a different model
            # Actual many to many|one results in circular dependancies
            self._relations[node] = [x for x in node.relations.values() if not isinstance(x, (tuple, list))]

    def changes(self, change_set):
        if self.__changes is not None:
            return self.__changes

        ordered, to_order = [], list(self._nodes.values())
        relations = {k: {(n['@id'], n['@type']) for n in v} for k, v in self._relations.items()}

        # Topologicallly sort graph nodes so relations can be properly built
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
                # See earlier note about ignoreing many to many|one
                if not isinstance(v, (tuple, list)):
                    # Attach all relations here so a proper change request can be generated
                    setattr(node.instance, k, self._nodes[(v['@id'], v['@type'])].instance)
            changes.append(node.change(change_set))
        self.__changes = changes
        return changes

    def change_set(self, submitter):
        if self.__change_set is not None:
            return self.__change_set

        self.__change_set = share.models.ChangeSet(submitted_by=submitter)
        self.__change_set.save()

        self.changes(self.__change_set)

        return self.__change_set
