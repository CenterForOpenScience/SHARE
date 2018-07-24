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
    def regulate_graph(self, graph):
        changed = True
        while changed:
            changed = False
            matcher = Matcher(GraphStrategy(graph))
            for matches in matcher.chunk_matches(graph):
                for node, dupes in matches.items():
                    if dupes:
                        changed = True
                    for dupe in dupes:
                        if dupe in graph and node in graph:
                            graph.merge_nodes(dupe, node)
                if changed:
                    break
