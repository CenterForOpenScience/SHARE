import pytest

from share.change import ChangeGraph
from share.disambiguation import GraphDisambiguator
from tests.share.normalize.factories import *


class TestPruneChangeGraph:
    def test_no_change(self):
        uri = 'http://osf.io/guidguid'
        nodes = Graph(
            Preprint(0, identifiers=[WorkIdentifier(1, uri=uri)])
        )
        graph = ChangeGraph(nodes, disambiguate=False)
        GraphDisambiguator().prune(graph)
        assert len(graph.nodes) == 2
        assert len(no_change_nodes) == len(graph.nodes)

    def test_duplicate_works(self):
        uri = 'http://osf.io/guidguid'
        nodes = Graph(
            Preprint(0, identifiers=[WorkIdentifier(1, uri=uri)]),
            CreativeWork(2, identifiers=[WorkIdentifier(3, uri=uri)])
        )
        graph = ChangeGraph(nodes, disambiguate=False)
        GraphDisambiguator().prune(graph)
        assert len(nodes) - 2 == len(graph.nodes)
