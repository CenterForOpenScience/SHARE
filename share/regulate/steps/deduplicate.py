
from share import exceptions
from share.regulate.steps import GraphStep
from share.util import DictHashingDict


class DupesNotMatchedError(exceptions.ShareException):
    pass


class MergingIncompatibleNodesError(exceptions.ShareException):
    pass


class Deduplicate(GraphStep):
    """Look for duplicate nodes and merge/discard them

    Example config (YAML):
        ```yaml
        - namespace: share.regulate.steps.graph
          name: deduplicate
        ```
    """
    def regulate_graph(self, graph):
        index = DupeNodeIndex()
        changed = True
        while changed:
            changed = False
            index.clear()
            for node in graph:
                dupe = index.get_match(node)
                if dupe:
                    self._merge_nodes(graph, node, dupe)
                    changed = True
                    break
                index.add(node)

    def _merge_nodes(self, graph, node_a, node_b):
        model_a, model_b = node_a.model, node_b.model
        if model_a._meta.concrete_model is not model_b._meta.concrete_model:
            raise MergingIncompatibleNodesError('Must have same concrete model', node_a, node_b)

        # Remove the node with the less specific class
        if issubclass(model_a, model_b):
            graph.merge_nodes(node_b, node_a)
        elif issubclass(model_b, model_a):
            graph.merge_nodes(node_a, node_b)
        else:
            # TODO handle this case
            raise MergingIncompatibleNodesError('Models must be related', node_a, node_b)

        # TODO
        #from share.models import Person
        #if replacement.model == Person:
        #    replacement.attrs['name'] = ''
        #    Person.normalize(replacement, replacement.graph)


class DupeNodeIndex:
    def __init__(self):
        self._index = {}
        self._node_cache = {}

    def clear(self):
        self._index.clear()
        self._node_cache.clear()

    def get_indexable_node(self, node):
        try:
            return self._node_cache[node]
        except KeyError:
            indexable_node = IndexableNode(node)
            self._node_cache[node] = indexable_node
            return indexable_node

    def add(self, node):
        indexable_node = self.get_indexable_node(node)
        by_model = self._index.setdefault(node.model._meta.concrete_model, DictHashingDict())
        if indexable_node.any:
            all_cache = by_model.setdefault(indexable_node.all, DictHashingDict())
            for item in indexable_node.any:
                all_cache.setdefault(item, []).append(node)
        elif indexable_node.all:
            by_model.setdefault(indexable_node.all, []).append(node)

    def remove(self, node):
        indexable_node = self.get_indexable_node(node)
        try:
            all_cache = self._index[node.model._meta.concrete_model][indexable_node.all]
            if indexable_node.any:
                for item in indexable_node.any:
                    all_cache[item].remove(node)
            else:
                all_cache.remove(node)
        except (KeyError, ValueError) as ex:
            raise ValueError('Could not remove node from cache: Node {} not found!'.format(node)) from ex

    def get_match(self, node):
        matches = self.get_matches()
        if not matches:
            return None
        if len(matches) != 1:
            raise DupesNotMatchedError
        return matches[0]

    def get_matches(self, node):
        indexable_node = self.get_indexable_node(node)
        matches = set()
        try:
            matches_all = self._index[node.model._meta.concrete_model][indexable_node.all]
            if indexable_node.any:
                for item in indexable_node.any:
                    matches.update(matches_all.get(item, []))
            elif indexable_node.all:
                matches.update(matches_all)
            # TODO use `indexable_node.tie_breaker` when there are multiple matches
            if indexable_node.matching_types:
                return [m for m in matches if m != node and m.model._meta.label_lower in indexable_node.matching_types]
            else:
                return [m for m in matches if m != node]
        except KeyError:
            return []


class IndexableNode:
    def __init__(self, node):
        self._node = node
        self.all = self._all()
        self.any = self._any()
        self.matching_types = self._matching_types()

    def _all(self):
        try:
            all = self._node.model.Disambiguation.all
        except AttributeError:
            return ()
        values = tuple((f, v) for f in all for v in self._field_values(f))
        assert len(values) == len(all)
        return values

    def _any(self):
        try:
            any = self._node.model.Disambiguation.any
        except AttributeError:
            return ()
        return tuple((f, v) for f in any for v in self._field_values(f))

    def _matching_types(self):
        try:
            constrain_types = self._node.model.Disambiguation.constrain_types
        except AttributeError:
            constrain_types = False
        if not constrain_types:
            return None

        # list of all subclasses and superclasses of node.model that could be the type of a node
        # TODO: stop using typedmodels like this -- make `@type` the concrete model and add a field for
        # subtype (e.g. {'@type': 'CreativeWork', 'subtype': 'Preprint'})
        # But not 'subtype'. Something better.
        model = self._node.model
        concrete_model = model._meta.concrete_model
        if concrete_model is model:
            type_names = [model._meta.label_lower]
        else:
            subclasses = model.get_types()
            superclasses = [m._meta.label_lower for m in model.__mro__ if issubclass(m, concrete_model) and m._meta.proxy]
            type_names = subclasses + superclasses
        return set(type_names)

    def _field_values(self, field_name):
        value = self._node[field_name]
        if isinstance(value, list):
            yield from value
        else:
            if value is not None and value != '':
                yield value
