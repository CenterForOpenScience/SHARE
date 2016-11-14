import pytest

from share.change import ChangeGraph
from share.models import ChangeSet
from share.disambiguation import GraphDisambiguator
from tests.share.normalize.factories import *


class TestPruneChangeGraph:
    @pytest.mark.parametrize('input', [
        [Preprint(0, identifiers=[WorkIdentifier(1, uri='http://osf.io/guidguid')])]
    ])
    def test_no_change(self, Graph, input):
        graph = ChangeGraph(Graph(*input))
        GraphDisambiguator().prune(graph)
        result = [n.serialize() for n in graph.nodes]
        assert result == Graph(*input)

    @pytest.mark.parametrize('input, output', [
        ([
            Preprint(0, identifiers=[WorkIdentifier(1, uri='http://osf.io/guidguid')]),
            CreativeWork(2, identifiers=[WorkIdentifier(3, uri='http://osf.io/guidguid')])
        ], [
            Preprint(0, identifiers=[WorkIdentifier(1, uri='http://osf.io/guidguid')]),
        ]),
        ([
            Preprint(0, identifiers=[
                WorkIdentifier(1, uri='http://osf.io/guidguid'),
                WorkIdentifier(4, uri='http://something.else')
            ]),
            CreativeWork(2, identifiers=[WorkIdentifier(3, uri='http://osf.io/guidguid')])
        ], [
            Preprint(0, identifiers=[
                WorkIdentifier(1, uri='http://osf.io/guidguid'),
                WorkIdentifier(4, uri='http://something.else')
            ]),
        ])
    ])
    def test_prune(self, Graph, input, output):
        graph = ChangeGraph(Graph(*input))
        GraphDisambiguator().prune(graph)
        result = [n.serialize() for n in graph.nodes]
        assert result == Graph(*output)

    @pytest.mark.parametrize('input', [
        [
            Preprint(0, identifiers=[WorkIdentifier(1, uri='http://osf.io/guidguid')])
        ],
        [
            Preprint(0, identifiers=[
                WorkIdentifier(1, uri='http://osf.io/guidguid'),
                WorkIdentifier(4, uri='http://something.else')
            ])
        ],
        [
            Article(
                title='Banana Stand',
                identifiers=[WorkIdentifier(uri='http://osf.io/guidguid')],
                agent_relations=[
                    Creator(agent=Person(name='Michael Bluth'), cited_as='Bluth M', order_cited=0),
                    Creator(agent=Person(name='Nichael Bluth'), cited_as='Bluth N', order_cited=1),
                    Publisher(agent=Organization(name='Bluth Company'), cited_as='Bluth Company')
                ],
                tags=[Tag(name='banana'), Tag(name='fraud')]
            )
        ],
    ])
    @pytest.mark.django_db
    def test_all_disambiguate(self, input, Graph, normalized_data_id):
        graph = ChangeGraph(Graph(*input))
        ChangeSet.objects.from_graph(graph, normalized_data_id).accept()

        GraphDisambiguator().find_instances(graph)
        assert all(n.instance for n in graph.nodes)
        assert all(n.instance._meta.model_name == n.type for n in graph.nodes)
