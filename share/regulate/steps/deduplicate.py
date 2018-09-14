from share.disambiguation.matcher import Matcher
from share.disambiguation.strategies import GraphStrategy
from share.regulate.steps import GraphStep


class Deduplicate(GraphStep):
    """Look for duplicate nodes and merge/discard them

    Example config (YAML):
        ```yaml
        - namespace: share.regulate.steps.graph
          name: deduplicate
        ```
    """
    MAX_MERGES = 100

    def regulate_graph(self, graph):
        count = 0
        while self._merge_first_dupe(graph):
            count += 1
            if count > self.MAX_MERGES:
                self.error('Way too many deduplications')
                return

    def _merge_first_dupe(self, graph):
        matcher = Matcher(GraphStrategy(graph))
        for matches in matcher.chunk_matches(graph):
            for node, dupes in matches.items():
                for dupe in dupes:
                    if dupe in graph and node in graph:
                        graph.merge_nodes(dupe, node)
                        return True
        return False
