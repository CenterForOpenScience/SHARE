import pytest

from share.legacy_normalize.regulate.steps.block_extra_values import BlockExtraValues
from share.util.graph import MutableGraph


class TestBlockExtraValuesStep:
    @pytest.fixture
    def graph(self):
        g = MutableGraph()
        g.add_node(1, 'creativework', {
            'title': 'A work!',
            'extra': {
                'foo': 'flooby',
                'bah': 'hab',
            },
        })
        g.add_node(2, 'creativework', {
            'title': 'Another work!',
            'extra': {
                'extra': 'extra',
                'bah': 'hab',
            },
        })
        g.add_node(3, 'creativework', {'title': 'No extra :('})
        return g

    @pytest.mark.parametrize('blocked_values, expected_nodes', [
        ({'foo': 'flooby'}, {2, 3}),
        ({'foo': 'flooby', 'match': 'nothing'}, {1, 2, 3}),
        ({'extra': 'extra'}, {1, 3}),
        ({'bah': 'hab'}, {3}),
    ])
    def test_block_extras(self, graph, blocked_values, expected_nodes):
        step = BlockExtraValues(blocked_values=blocked_values)
        for node in list(graph):
            step.regulate_node(node)
            if node.id in expected_nodes:
                assert node in graph
            else:
                assert node not in graph
        assert len(graph) == len(expected_nodes)

    def test_error_on_bad_setting(self):
        with pytest.raises(TypeError):
            BlockExtraValues(bad_setting=True)

        # blocked_values required, must be non-empty dict
        with pytest.raises(TypeError):
            BlockExtraValues()
        with pytest.raises(TypeError):
            BlockExtraValues(blocked_values=['bad'])
        with pytest.raises(TypeError):
            BlockExtraValues(blocked_values={})
        BlockExtraValues(blocked_values={'this': 'works'})
