from django.conf import settings

from share.util.extensions import Extensions


class Regulator:
    VERSION = 1

    def __init__(self, ingest_job=None):
        self.job = ingest_job
        self.logs = []

        self._graph_steps = self._steps('share.regulate.graph_steps', settings.SHARE_REGULATOR_GRAPH_STEPS)
        self._node_steps = self._steps('share.regulate.node_steps', settings.SHARE_REGULATOR_NODE_STEPS)
        self._validation_steps = self._steps('share.regulate.validation_steps', settings.SHARE_REGULATOR_VALIDATION_STEPS)

    def regulate(self, graph):
        try:
            # TODO get source-specific steps (and options) from self.job.suid.source_config, run them first

            # Node phase
            for node in self._iter_nodes(graph):
                for step in self._node_steps:
                    if step.should_regulate(node):
                        step.regulate_node(node)

            # Graph phase
            for step in self._graph_steps:
                step.regulate_graph(graph)

            # Validation phase
            for step in self._validation_steps:
                step.validate_graph(graph)

        finally:
            if self.job and self.logs:
                self.job.regulator_logs.set(self.logs)

    def _iter_nodes(self, graph):
        """Iterate through the graph's nodes in no particular order, allowing nodes to be added/deleted while iterating
        """
        visited = set()
        nodes = list(graph)
        while nodes:
            for n in nodes:
                if n in graph:
                    yield n
                    visited.add(n)
            nodes = set(graph) - visited

    def _steps(self, namespace, names):
        return [Extensions.get(namespace, name)(self) for name in names]
