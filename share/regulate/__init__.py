from django.conf import settings

from share.models import RegulatorLog
from share.util.extensions import Extensions
from share.regulate.steps import NodeStep, GraphStep, ValidationStep


class Regulator:
    VERSION = 1

    def __init__(self, ingest_job=None, source_config=None, steps_config=None):
        assert not ingest_job or not source_config, 'Provider ingest_job or source_config, not both'

        self.job = ingest_job
        self._logs = []

        config = settings.SHARE_REGULATOR_STEPS if steps_config is None else steps_config
        self._default_steps = self._get_steps(config)
        self._custom_steps = []

        if ingest_job and not source_config:
            source_config = ingest_job.suid.source_config

        if source_config:
            self._custom_steps = self._get_steps(source_config.regulator_steps)

    def regulate(self, graph):
        try:
            for step in self._custom_steps:
                self._run_step(step, graph)
            for step in self._default_steps:
                self._run_step(step, graph)
        finally:
            if self.job and self._logs:
                for log in self._logs:
                    log.ingest_job = self.job
                RegulatorLog.objects.bulk_create(self._logs)

    def _run_step(self, step, graph):
        try:
            if isinstance(step, NodeStep):
                for node in self._iter_nodes(graph):
                    if step.valid_target(node):
                        step.regulate_node(node)
            elif isinstance(step, GraphStep):
                step.regulate_graph(graph)
            elif isinstance(step, ValidationStep):
                step.validate_graph(graph)
        finally:
            if step.logs:
                self._logs.extend(step.logs)

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

    def _get_steps(self, step_configs):
        if not step_configs:
            return []
        return [self._get_step(**config) for config in step_configs]

    def _get_step(self, namespace, name, settings=None):
        """Instantiate and return a regulator step for the given config.

        Params:
            namespace: Name of the step's entry point group in setup.py
            name: Name of the step's entry point in setup.py
            [settings]: Optional dictionary, passed as keyword arguments when initializing the step
        """
        return Extensions.get(namespace, name)(**(settings or {}))
