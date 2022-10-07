from share.legacy_normalize.regulate.steps import GraphStep


class Deduplicate(GraphStep):
    """Look for duplicate nodes and merge/discard them

    Example config (YAML):
        ```yaml
        - namespace: share.regulate.steps.graph
          name: deduplicate
        ```
    """
    MAX_MERGES = 100

    # map from concrete type to set of fields used to dedupe
    DEDUPLICATION_CRITERIA = {
        # works and agents may be merged if duplicate identifiers are merged
        # 'abstractcreativework': {},
        # 'abstractagent': {},
        'abstractagentworkrelation': {'creative_work', 'agent', 'type'},
        'abstractagentrelation': {'subject', 'related', 'type'},
        'abstractworkrelation': {'subject', 'related', 'type'},
        'workidentifier': {'uri'},
        'agentidentifier': {'uri'},
        'subject': {'name', 'parent', 'central_synonym'},
        'tag': {'name'},
        'throughtags': {'tag', 'creative_work'},
        # 'award': {},
        'throughawards': {'funder', 'award'},
        'throughsubjects': {'subject', 'creative_work'},
    }

    def regulate_graph(self, graph):
        # naive algorithm, O(n*m) (n: number of nodes, m: number of merges)
        # but merges shouldn't be common, so probably not worth optimizing
        count = 0
        while self._merge_first_dupe(graph):
            count += 1
            if count > self.MAX_MERGES:
                self.error('Way too many deduplications')
                return

    def _merge_first_dupe(self, graph):
        dupe_index = {}
        for node in graph:
            node_key = self._get_node_key(node)
            if node_key:
                other_node = dupe_index.get(node_key)
                if other_node:
                    graph.merge_nodes(node, other_node)
                    return True
                dupe_index[node_key] = node
        return False

    def _get_node_key(self, node):
        criteria = self.DEDUPLICATION_CRITERIA.get(node.concrete_type)
        if not criteria:
            return None
        return (
            node.concrete_type,
            tuple(
                self._get_criterion_value(node, criterion)
                for criterion in criteria
            )
        )

    def _get_criterion_value(self, node, criterion_name):
        if criterion_name == 'type':
            return node.type
        return node[criterion_name]
