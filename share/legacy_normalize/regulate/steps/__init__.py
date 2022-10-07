import abc

from share.exceptions import RegulateError
from share.models import RegulatorLog


class BaseStep(abc.ABC):
    logs = None

    def __init__(self):
        self.logs = []

    def info(self, description, node_id=None):
        """Log information about a change made to the graph.
        """
        log = RegulatorLog(description=description, rejected=False, node_id=node_id)
        self.logs.append(log)

    def error(self, description, node_id=None, exception=None):
        """Indicate a severe problem with the data, halt regulation.
        """
        log = RegulatorLog(description=description, rejected=True, node_id=node_id)
        self.logs.append(log)
        raise RegulateError('Regulation failed: {}'.format(description)) from exception

    @abc.abstractmethod
    def run(self, graph):
        raise NotImplementedError


class NodeStep(BaseStep):
    node_types = None

    def __init__(self, *args, node_types=None, **kwargs):
        """Initialize a NodeStep.

        Params:
            regulator: Regulator instance
            [node_types]: List of node types this step will be run on. e.g. ['WorkIdentifier']
        """
        super().__init__(*args, **kwargs)

        if node_types:
            self.node_types = [t.lower() for t in node_types]

    def valid_target(self, node):
        """Return True if `node` is a valid target for this regulator step.

        Override to filter the nodes this step will run on.
        """
        if self.node_types is None:
            return True
        return (node.type in self.node_types or node.concrete_type in self.node_types)

    @abc.abstractmethod
    def regulate_node(self, node):
        raise NotImplementedError

    def run(self, graph):
        self.logs.clear()
        for node in self._iter_nodes(graph):
            if self.valid_target(node):
                self.regulate_node(node)

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


class GraphStep(BaseStep):
    def run(self, graph):
        self.logs.clear()
        self.regulate_graph(graph)

    @abc.abstractmethod
    def regulate_graph(self, graph):
        raise NotImplementedError


class ValidationStep(BaseStep):
    def run(self, graph):
        self.logs.clear()
        # TODO: convert to read-only graph?
        self.validate_graph(graph)

    @abc.abstractmethod
    def validate_graph(self, graph):
        """Validate the graph.

        Call `self.reject` or `self.fail` if the graph is invalid.
        Must not modify the graph in any way.
        """
        raise NotImplementedError

    def reject(self, description, node_id=None, exception=None):
        """Indicate a regulated graph failed validation and will not be merged into the SHARE dataset.
        """
        log = RegulatorLog(description=description, rejected=True, node_id=node_id)
        self.logs.append(log)
        raise RegulateError('Graph failed validation: {}'.format(description)) from exception
