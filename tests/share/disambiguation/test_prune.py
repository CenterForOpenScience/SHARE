import pytest

from share.change import ChangeGraph
from share.models import ChangeSet
from share.disambiguation import GraphDisambiguator
from tests.share.normalize.factories import *


class TestPruneChangeGraph:
    @pytest.mark.parametrize('input', [
        [Preprint(0, identifiers=[WorkIdentifier(1)])]
    ])
    def test_no_change(self, Graph, input):
        graph = ChangeGraph(Graph(*input))
        GraphDisambiguator().prune(graph)
        result = [n.serialize() for n in graph.nodes]
        assert result == Graph(*input)

    @pytest.mark.parametrize('input, output', [
        ([
            Preprint(0, identifiers=[WorkIdentifier(id=1, uri='http://osf.io/guidguid')]),
            CreativeWork(id=1, sparse=True, identifiers=[WorkIdentifier(uri='http://osf.io/guidguid')])
        ], [
            Preprint(0, identifiers=[WorkIdentifier(uri='http://osf.io/guidguid')]),
        ]),
        ([
            Preprint(0, identifiers=[
                WorkIdentifier(uri='http://osf.io/guidguid'),
                WorkIdentifier(4)
            ]),
            CreativeWork(id=1, sparse=True, identifiers=[WorkIdentifier(uri='http://osf.io/guidguid')])
        ], [
            Preprint(0, identifiers=[
                WorkIdentifier(uri='http://osf.io/guidguid'),
                WorkIdentifier(4)
            ]),
        ])
    ])
    def test_prune(self, Graph, input, output):
        graph = ChangeGraph(Graph(*input))
        GraphDisambiguator().prune(graph)
        result = [n.serialize() for n in graph.nodes]
        assert result == Graph(*output)

    @pytest.mark.django_db
    @pytest.mark.parametrize('input', [
        [
            Preprint(identifiers=[WorkIdentifier()])
        ],
        [
            Preprint(identifiers=[
                WorkIdentifier(),
                WorkIdentifier()
            ])
        ],
        [
            Article(
                identifiers=[WorkIdentifier()],
                agent_relations=[
                    Creator(agent=Person()),
                    Creator(agent=Person()),
                    Publisher(agent=Organization())
                ],
                tags=[Tag(), Tag()]
            )
        ],
    ])
    def test_all_disambiguate(self, input, Graph, normalized_data_id):
        graph = ChangeGraph(Graph(*input))
        ChangeSet.objects.from_graph(graph, normalized_data_id).accept()

        assert all(n.instance is None for n in graph.nodes)
        GraphDisambiguator().find_instances(graph)
        assert all(n.instance for n in graph.nodes)
        assert all(n.instance._meta.model_name == n.type for n in graph.nodes)
