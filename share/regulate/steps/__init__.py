from share.exceptions import RegulateError
from share.models import RegulatorLog


class BaseStep:
    def __init__(self, regulator, **options):
        self.regulator = regulator
        self.options = options

    def info(self, description, node_id=None):
        """Log information about a change made to the graph.
        """
        self.regulator.logs.append(RegulatorLog(description=description, node_id=node_id))

    def error(self, description, node_id=None, exception=None):
        """Indicate a severe problem with the data, halt regulation.
        """
        self.regulator.logs.append(RegulatorLog(description=description, rejected=True, node_id=node_id))
        raise RegulateError('Regulation failed: {}'.format(description)) from exception


class NodeStep(BaseStep):
    def valid_target(self, node):
        """Return True if `node` is a valid target for this regulator step.

        Override to filter the nodes this step will run on.
        """
        return True

    def regulate_node(self, node):
        raise NotImplementedError()


class GraphStep(BaseStep):
    def regulate_graph(self, graph):
        raise NotImplementedError()


class ValidationStep(BaseStep):
    def validate_graph(self, graph):
        """Validate the graph.

        Call `self.reject` or `self.fail` if the graph is invalid.
        Must not modify the graph in any way.
        """
        raise NotImplementedError()

    def reject(self, description, node_id=None, exception=None):
        """Indicate a regulated graph failed validation and will not be merged into the SHARE dataset.
        """
        self.regulator.logs.append(RegulatorLog(description=description, rejected=True, node_id=node_id))
        raise RegulateError('Graph failed validation: {}'.format(description)) from exception
