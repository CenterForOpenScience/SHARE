import pytest

from share.change import ChangeGraph
from share.disambiguation import GraphDisambiguator
from tests.share.normalize.factories import *


class TestPruneChangeGraph:
    @pytest.mark.parametrize('input', [
        [Preprint('_:0', identifiers=[WorkIdentifier('_:1', uri='http://osf.io/guidguid')])]
    ])
    def test_no_change(self, Graph, input):
        graph = ChangeGraph(Graph(*input))
        GraphDisambiguator().prune(graph)
        result = [n.serialize() for n in graph.nodes]
        assert result == Graph(*input)

    @pytest.mark.parametrize('input, output', [
        ([
            Preprint('_:0', identifiers=[WorkIdentifier('_:1', uri='http://osf.io/guidguid')]),
            CreativeWork('_:2', identifiers=[WorkIdentifier('_:3', uri='http://osf.io/guidguid')])
        ], [
            Preprint('_:0', identifiers=[WorkIdentifier('_:1', uri='http://osf.io/guidguid')]),
        ]),
        ([
            Preprint('_:0', identifiers=[
                WorkIdentifier('_:1', uri='http://osf.io/guidguid'),
                WorkIdentifier('_:4', uri='http://something.else')
            ]),
            CreativeWork('_:2', identifiers=[WorkIdentifier('_:3', uri='http://osf.io/guidguid')])
        ], [
            Preprint('_:0', identifiers=[
                WorkIdentifier('_:1', uri='http://osf.io/guidguid'),
                WorkIdentifier('_:4', uri='http://something.else')
            ]),
        ])
    ])
    def test_prune(self, Graph, input, output):
        graph = ChangeGraph(Graph(*input))
        GraphDisambiguator().prune(graph)
        result = [n.serialize() for n in graph.nodes]
        assert result == Graph(*output)
