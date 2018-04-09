from share import exceptions
from share.disambiguation import DisambiguationInfo
from share.regulate.steps import GraphStep
from share.regulate.steps.normalize_agent_names import NormalizeAgentNames
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

        from_node, into_node = None, None
        # Remove the node with the less specific class
        if issubclass(model_a, model_b):
            from_node = node_b
            into_node = node_a
        elif issubclass(model_b, model_a):
            from_node = node_a
            into_node = node_b
        else:
            # TODO handle this case
            raise MergingIncompatibleNodesError('Models must be related', node_a, node_b)

        graph.merge_nodes(from_node, into_node)

        # TODO: run all node steps on `into_node`?
        normalize_name = NormalizeAgentNames()
        if normalize_name.valid_target(into_node):
            normalize_name.regulate_node(into_node)


class DupeNodeIndex:
    def __init__(self):
        self._index = {}
        self._node_cache = {}

    def clear(self):
        self._index.clear()
        self._node_cache.clear()

    def get_node_info(self, node):
        try:
            return self._node_cache[node]
        except KeyError:
            node_info = DisambiguationInfo(node)
            self._node_cache[node] = node_info
            return node_info

    def add(self, node):
        node_info = self.get_node_info(node)
        by_model = self._index.setdefault(node.model._meta.concrete_model, DictHashingDict())
        if node_info.any:
            all_cache = by_model.setdefault(node_info.all, DictHashingDict())
            for item in node_info.any:
                all_cache.setdefault(item, []).append(node)
        elif node_info.all:
            by_model.setdefault(node_info.all, []).append(node)

    def remove(self, node):
        node_info = self.get_node_info(node)
        try:
            all_cache = self._index[node.model._meta.concrete_model][node_info.all]
            if node_info.any:
                for item in node_info.any:
                    all_cache[item].remove(node)
            else:
                all_cache.remove(node)
        except (KeyError, ValueError) as ex:
            raise ValueError('Could not remove node from cache: Node {} not found!'.format(node)) from ex

    def get_match(self, node):
        matches = self.get_matches(node)
        if not matches:
            return None
        if len(matches) != 1:
            raise DupesNotMatchedError
        return matches[0]

    def get_matches(self, node):
        node_info = self.get_node_info(node)
        matches = set()
        try:
            matches_all = self._index[node.model._meta.concrete_model][node_info.all]
            if node_info.any:
                for item in node_info.any:
                    matches.update(matches_all.get(item, []))
            elif node_info.all:
                matches.update(matches_all)
            # TODO use `node_info.tie_breaker` when there are multiple matches
            if node_info.matching_types:
                return [m for m in matches if m != node and m.model._meta.label_lower in node_info.matching_types]
            else:
                return [m for m in matches if m != node]
        except KeyError:
            return []
