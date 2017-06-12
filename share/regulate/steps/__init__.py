from share.regulate.errors import RegulatorError


class BaseStep:
    def __init__(self, job):
        self.job = job

    def info(self, description, node_id=None):
        """Log information about a change made to the graph.
        """
        # TODO keep a list of logs, save them at the end?
        self.job.regulator_logs.create(description=description, node_id=node_id)

    def reject(self, description, node_id=None):
        """Indicate a regulated graph can be saved, but will not be merged into the SHARE dataset.
        """
        self.job.regulator_logs.create(description=description, node_id=node_id)
        # TODO don't merge suid with anything else

    def fail(self, description, node_id=None):
        """Indicate a severe problem with the data, halt regulation.
        """
        self.job.regulator_logs.create(description=description, rejected=True, node_id=node_id)
        raise RegulatorError('Regulation failed: {}'.format(description))


class BaseGraphStep(BaseStep):
    def regulate_graph(self, graph):
        raise NotImplementedError()


class BaseNodeStep(BaseStep):
    def regulate_node(self, node):
        raise NotImplementedError()


class BaseValidationStep(BaseStep):
    def validate_graph(self, graph):
        raise NotImplementedError()
