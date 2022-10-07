import pytest
from unittest import mock

from share.legacy_normalize.regulate.regulator import Regulator, Steps, InfiniteRegulationError, RegulatorConfigError
from share.legacy_normalize.regulate.steps import NodeStep, GraphStep, ValidationStep
from share.util.graph import MutableGraph


@pytest.mark.parametrize('num_node_steps', [0, 1, 5])
@pytest.mark.parametrize('num_graph_steps', [0, 1, 5])
@pytest.mark.parametrize('num_validation_steps', [0, 1, 5])
@pytest.mark.parametrize('num_nodes', range(0, 100, 20))
class TestRegulatorCallsRun:

    @pytest.fixture
    def mock_steps(self, monkeypatch, num_node_steps, num_graph_steps, num_validation_steps):
        mock_steps = {
            'node': [mock.Mock(NodeStep, logs=[]) for _ in range(num_node_steps)],
            'graph': [mock.Mock(GraphStep, logs=[]) for _ in range(num_graph_steps)],
            'validate': [mock.Mock(ValidationStep, logs=[]) for _ in range(num_validation_steps)],
        }

        def patched_steps(self, _, namespace):
            return mock_steps[namespace.split('.')[-1]]

        monkeypatch.setattr(Steps, '_load_steps', patched_steps)
        return mock_steps

    def test_calls_run(self, mock_steps, num_nodes):
        graph = MutableGraph()
        for i in range(num_nodes):
            graph.add_node(i, 'creativework')
        Regulator(regulator_config={'not': 'empty'}).regulate(graph)
        assert all(s.run.call_count == 1 for st in mock_steps.values() for s in st)


class InfiniteGraphStep(GraphStep):
    counter = 0

    def regulate_graph(self, graph):
        node = next(n for n in graph)
        node['foo'] = self.counter
        self.counter += 1


class TestRegulatorError:

    def test_infinite_regulate(self):
        reg = Regulator()
        reg._default_steps.graph_steps = (InfiniteGraphStep(),)
        graph = MutableGraph()
        graph.add_node(None, 'agent', {'name': 'Agent Agent'})
        with pytest.raises(InfiniteRegulationError):
            reg.regulate(graph)

    @pytest.mark.parametrize('config', [
        {'NODE_STEPS': 7},
        {'NODE_STEPS': [7]},
        {'GRAPH_STEPS': 'NODE_STEPS'},
    ])
    def test_broken_config(self, config):
        with pytest.raises(RegulatorConfigError):
            Regulator(regulator_config=config)
