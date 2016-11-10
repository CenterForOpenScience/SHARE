import pytest

from share.change import ChangeGraph
from share.disambiguation import GraphDisambiguator

@pytest.fixture
def no_change_nodes():
    return [{
        '@id': '_:91011',
        '@type': 'preprint',
        'contributors': [{'@id': '_:5678', '@type': 'contributor'}],
        'identifiers': [{'@id': '_:6789', '@type': 'workidentifier'}]
    }, {
        '@id': '_:5678',
        '@type': 'contributor',
        'agent': {
            '@id': '_:1234',
            '@type': 'person'
        },
        'creative_work': {
            '@id': '_:91011',
            '@type': 'preprint'
        },
    }, {
        '@id': '_:1234',
        '@type': 'person',
        'given_name': 'Doe',
        'family_name': 'Jane',
    }, {
        '@id': '_:6789',
        '@type': 'workidentifier',
        'uri': 'http://osf.io/guidguid',
        'creative_work': {'@id': '_:91011', '@type': 'preprint'}
    }]

@pytest.fixture
def dup_work_nodes():
    return [{
        '@id': '_:91011',
        '@type': 'preprint',
        'contributors': [{'@id': '_:5678', '@type': 'contributor'}],
        'identifiers': [{'@id': '_:6789', '@type': 'workidentifier'}]
    }, {
        '@id': '_:5678',
        '@type': 'contributor',
        'agent': {
            '@id': '_:1234',
            '@type': 'person'
        },
        'creative_work': {
            '@id': '_:91011',
            '@type': 'preprint'
        },
    }, {
        '@id': '_:1234',
        '@type': 'person',
        'given_name': 'Doe',
        'family_name': 'Jane',
    }, {
        '@id': '_:6789',
        '@type': 'workidentifier',
        'uri': 'http://osf.io/guidguid',
        'creative_work': {'@id': '_:91011', '@type': 'preprint'}
    }, {
        '@id': '_:91012',
        '@type': 'creativework',
        'identifiers': [{'@id': '_:6780', '@type': 'workidentifier'}]
    }, {
        '@id': '_:6780',
        '@type': 'workidentifier',
        'uri': 'http://osf.io/guidguid',
        'creative_work': {'@id': '_:91012', '@type': 'creativework'}
    }]



class TestPruneChangeGraph:
    def test_no_change(self, no_change_nodes):
        graph = ChangeGraph(no_change_nodes, disambiguate=False)
        GraphDisambiguator().prune(graph)
        assert len(no_change_nodes) == len(graph.nodes)

    def test_duplicate_works(self, dup_work_nodes):
        graph = ChangeGraph(dup_work_nodes, disambiguate=False)
        GraphDisambiguator().prune(graph)
        assert len(dup_work_nodes) - 2 == len(graph.nodes)
