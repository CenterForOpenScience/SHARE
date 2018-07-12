from django.conf import settings

from share import exceptions
from share.models import RegulatorLog
from share.util.extensions import Extensions


class RegulatorConfigError(exceptions.ShareException):
    pass


class InfiniteRegulationError(exceptions.ShareException):
    pass


class Regulator:
    VERSION = 1

    def __init__(
            self,
            ingest_job=None,
            source_config=None,
            regulator_config=None,
            validate=True,
    ):
        assert not ingest_job or not source_config, 'Provider ingest_job or source_config, not both'

        self.job = ingest_job
        self._logs = []

        if ingest_job and not source_config:
            source_config = ingest_job.suid.source_config

        self._custom_steps = Steps(
            self,
            source_config.regulator_steps if source_config else None,
            validate=validate,
        )
        self._default_steps = Steps(
            self,
            regulator_config or settings.SHARE_REGULATOR_CONFIG,
            validate=validate
        )

    def regulate(self, graph):
        try:
            self._custom_steps.run(graph)
            self._default_steps.run(graph)
        finally:
            if self.job and self._logs:
                for log in self._logs:
                    log.ingest_job = self.job
                RegulatorLog.objects.bulk_create(self._logs)


class Steps:
    MAX_RUNS = 31

    node_steps = ()
    graph_steps = ()
    validate_steps = ()

    def __init__(self, regulator, regulator_config, node=True, graph=True, validate=True):
        self.regulator = regulator
        if not regulator_config:
            return
        if node:
            self.node_steps = self._load_steps(regulator_config.get('NODE_STEPS'), 'share.regulate.steps.node')
        if graph:
            self.graph_steps = self._load_steps(regulator_config.get('GRAPH_STEPS'), 'share.regulate.steps.graph')
        if validate:
            self.validate_steps = self._load_steps(regulator_config.get('VALIDATE_STEPS'), 'share.regulate.steps.validate')

    def run(self, graph):
        runs = 0
        while True:
            self._run_steps(graph, self.node_steps)

            graph.changed = False
            self._run_steps(graph, self.graph_steps)
            if not graph.changed:
                break

            runs += 1
            if runs >= self.MAX_RUNS:
                raise InfiniteRegulationError
        self._run_steps(graph, self.validate_steps)

    def _run_steps(self, graph, steps):
        for step in steps:
            try:
                step.run(graph)
            finally:
                if step.logs:
                    self.regulator._logs.extend(step.logs)

    def _load_steps(self, step_configs, namespace):
        try:
            steps = []
            for step in (step_configs or []):
                if isinstance(step, str):
                    steps.append(self._load_step(namespace, step))
                elif isinstance(step, (list, tuple)) and len(step) == 2:
                    steps.append(self._load_step(namespace, step[0], step[1]))
                else:
                    raise RegulatorConfigError('Each step must be a string or (name, settings) pair. Got: {}'.format(step))
            return tuple(steps)
        except Exception:
            raise RegulatorConfigError('Error loading regulator step config for namespace {}'.format(namespace))

    def _load_step(self, namespace, name, settings=None):
        """Instantiate and return a regulator step for the given config.

        Params:
            namespace: Name of the step's entry point group in setup.py
            name: Name of the step's entry point in setup.py
            [settings]: Optional dictionary, passed as keyword arguments when initializing the step
        """
        return Extensions.get(namespace, name)(**(settings or {}))
