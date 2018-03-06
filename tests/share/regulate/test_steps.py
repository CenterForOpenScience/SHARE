import pytest
from unittest import mock

from share.regulate.steps import NodeStep, GraphStep, ValidationStep
from share.regulate.steps.normalize_iris import NormalizeIRIs
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
