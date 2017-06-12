from django.conf import settings

from share.util.extensions import Extensions
from share.regulate.errors import RegulatorError


class Regulator:
    VERSION = 1

    def __init__(self, ingest_job):
        self.job = ingest_job
        self._graph_steps = self._steps('share.regulate.graph_steps', settings.SHARE_REGULATOR_GRAPH_STEPS)
        self._node_steps = self._steps('share.regulate.node_steps', settings.SHARE_REGULATOR_NODE_STEPS)
        self._validation_steps = self._steps('share.regulate.validation_steps', settings.SHARE_REGULATOR_VALIDATION_STEPS)

    def regulate(self, graph):
        try:
            # TODO get source-specific steps from self.job.suid.source_config, run them first

            for step in self._graph_steps:
                step.regulate_graph(graph)

            for node in graph:
                # TODO also run node steps for newly created nodes
                for step in self._node_steps:
                    step.regulate_node(node)

            for step in self._validation_steps:
                step.validate_graph(graph)

        except RegulatorError as e:
            # TODO
            raise e

    def _steps(self, namespace, names):
        return [Extensions.get(namespace, name)(self.job) for name in names]
