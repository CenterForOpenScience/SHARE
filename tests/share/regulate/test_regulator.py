import pytest
from unittest import mock

from share.regulate import Regulator
from share.regulate.steps import NodeStep, GraphStep, ValidationStep
from share.util.graph import MutableGraph


@pytest.mark.parametrize('num_node_steps', [0, 1, 5])
@pytest.mark.parametrize('num_graph_steps', [0, 1, 5])
@pytest.mark.parametrize('num_validation_steps', [0, 1, 5])
@pytest.mark.parametrize('num_nodes', range(0, 100, 20))
class TestRegulator:

    @pytest.fixture
    def steps(self, monkeypatch, num_node_steps, num_graph_steps, num_validation_steps):
        node_steps = [mock.Mock(NodeStep, logs=[]) for _ in range(num_node_steps)]
        graph_steps = [mock.Mock(GraphStep, logs=[]) for _ in range(num_graph_steps)]
        validation_steps = [mock.Mock(ValidationStep, logs=[]) for _ in range(num_validation_steps)]

        def patched_steps(cls, _):
            return [
                *node_steps,
                *graph_steps,
                *validation_steps,
            ]

        monkeypatch.setattr(Regulator, '_get_steps', patched_steps)
        return {'node': node_steps, 'graph': graph_steps, 'validation': validation_steps}

    def test_calls_steps(self, steps, num_nodes):
        graph = MutableGraph()
        for i in range(num_nodes):
            graph.add_node(i, 'creativework')
        Regulator().regulate(graph)
        assert all(m.valid_target.call_count == num_nodes for m in steps['node'])
        assert all(m.regulate_node.call_count == num_nodes for m in steps['node'])
        assert all(m.regulate_graph.call_count == 1 for m in steps['graph'])
        assert all(m.validate_graph.call_count == 1 for m in steps['validation'])
