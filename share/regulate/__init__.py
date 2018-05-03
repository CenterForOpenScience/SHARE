from django.conf import settings

from share import exceptions
from share.models import RegulatorLog
from share.util.extensions import Extensions


class RegulatorConfigError(exceptions.ShareError):
    pass


class Regulator:
    VERSION = 1

    def __init__(self, ingest_job=None, source_config=None, regulator_config=None):
        assert not ingest_job or not source_config, 'Provider ingest_job or source_config, not both'

        self.job = ingest_job
        self._logs = []

        if ingest_job and not source_config:
            source_config = ingest_job.suid.source_config

        self._custom_steps = Steps(source_config.regulator_steps if source_config else None)
        self._default_steps = Steps(regulator_config or settings.SHARE_REGULATOR_CONFIG)

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
            step.run(graph)
        finally:
            if step.logs:
                self._logs.extend(step.logs)


class Steps:
    node_steps = ()
    graph_steps = ()
    validate_steps = ()

    def __init__(self, regulator_config):
        if not regulator_config:
            return
        self.node_steps = self._get_steps(regulator_config.get('NODE_STEPS'), 'share.regulate.steps.node')
        self.graph_steps = self._get_steps(regulator_config.get('GRAPH_STEPS'), 'share.regulate.steps.graph')
        self.validate_steps = self._get_steps(regulator_config.get('VALIDATE_STEPS'), 'share.regulate.steps.validate')

    def __iter__(self):
        yield from self.node_steps
        yield from self.graph_steps
        yield from self.validate_steps

    def _get_steps(self, step_configs, namespace):
        steps = []
        for step in (step_configs or []):
            if isinstance(step, str):
                steps.append(self._get_step(namespace, step))
            elif isinstance(step, (list, tuple)) and len(step) == 2:
                steps.append(self._get_step(namespace, step[0], step[1]))
            else:
                raise RegulatorConfigError('Each step must be a string or (name, settings) pair. Got: {}'.format(step))
        return tuple(steps)

    def _get_step(self, namespace, name, settings=None):
        """Instantiate and return a regulator step for the given config.

        Params:
            namespace: Name of the step's entry point group in setup.py
            name: Name of the step's entry point in setup.py
            [settings]: Optional dictionary, passed as keyword arguments when initializing the step
        """
        return Extensions.get(namespace, name)(**(settings or {}))
