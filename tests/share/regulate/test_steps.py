import pytest

from share.regulate.steps import NodeStep, GraphStep, ValidationStep
from share.regulate.steps.normalize_iris import NormalizeIRIs
from share.regulate.steps.block_extra_values import BlockExtraValues
from share.util.extensions import Extensions
from share.util.graph import MutableGraph


@pytest.mark.parametrize('namespace, base_class', [
    ('share.regulate.steps.node', NodeStep),
    ('share.regulate.steps.graph', GraphStep),
    ('share.regulate.steps.validate', ValidationStep),
])
def test_step_bases(namespace, base_class):
    assert all(issubclass(e.plugin, base_class) for e in Extensions._load_namespace(namespace))


# test normalize_iri
# test block_extra_values

class TestNormalizeIRIsStep:
    IDENTIFIERS = [
        # (uri, scheme, authority)
        ('http://osf.io/mst3k/', 'http', 'osf.io'),
        ('mailto:foo@example.com', 'mailto', 'example.com'),
        ('2049-3630', 'urn', 'issn'),
        ('0000-0002-1825-0097', 'http', 'orcid.org'),
    ]

    @pytest.fixture
    def graph(self):
        g = MutableGraph()
        g.add_node('work', 'creativework', title='This is a work!')
        return g

    @pytest.mark.parametrize('schemes, authorities, expected_identifiers', [
        ([], [], 4),
        (['mailto'], [], 3),
        (['mailto', 'http'], [], 1),
        ([], ['issn'], 3),
        ([], ['osf.io', 'foo'], 3),
        (['nothing'], ['everything'], 4),
        (['http'], ['example.com', 'issn'], 0),
    ])
    def test_regulate_nodes(self, graph, schemes, authorities, expected_identifiers):
        step = NormalizeIRIs(blocked_schemes=schemes, blocked_authorities=authorities)

        for uri, scheme, authority in self.IDENTIFIERS:
            node = graph.add_node('id_{}'.format(authority), 'workidentifier', uri=uri, creative_work='work')
            assert node['scheme'] is None
            assert node['host'] is None

            step.regulate_node(node)

            if scheme not in schemes and authority not in authorities:
                assert node['scheme'] == scheme
                assert node['host'] == authority

        assert len(graph.filter_type('workidentifier')) == expected_identifiers

    def test_error_on_bad_settings(self):
        with pytest.raises(TypeError):
            NormalizeIRIs(bad_setting=True)

        # No required settings
        NormalizeIRIs()


class TestBlockExtraValuesStep:
    @pytest.fixture
    def graph(self):
        g = MutableGraph()
        g.add_node(1, 'creativework', title='A work!', extra={
            'foo': 'flooby',
            'bah': 'hab',
        })
        g.add_node(2, 'creativework', title='Another work!', extra={
            'extra': 'extra',
            'bah': 'hab',
        })
        g.add_node(3, 'creativework', title='No extra :(')
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
