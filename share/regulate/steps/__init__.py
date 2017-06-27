from share.models import RegulatorLog
from share.regulate.errors import RegulatorError


class BaseStep:
    def __init__(self, regulator):
        self.regulator = regulator

    def info(self, description, node_id=None):
        """Log information about a change made to the graph.
        """
        self.regulator.logs.append(RegulatorLog(description=description, node_id=node_id))

    def reject(self, description, node_id=None):
        """Indicate a regulated graph can be saved, but will not be merged into the SHARE dataset.
        """
        # TODO don't merge suid with anything else, but let ingestion continue
        self.regulator.logs.append(RegulatorLog(description=description, rejected=True, node_id=node_id))

    def fail(self, description, node_id=None):
        """Indicate a severe problem with the data, halt regulation.
        """
        self.regulator.logs.append(RegulatorLog(description=description, rejected=True, node_id=node_id))
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
