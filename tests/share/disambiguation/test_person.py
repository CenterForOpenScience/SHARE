import pytest

from share import models
from share.change import ChangeGraph
from share.models import ChangeSet

from tests.share.models.factories import NormalizedDataFactory
from tests.share.normalize.factories import *


initial = [
    Preprint(
        identifiers=[WorkIdentifier(1)],
        agent_relations=[
            Contributor(agent=Person(1, name='Bob Dylan')),
            Creator(agent=Person(2)),
            Creator(agent=Person(3)),
        ]
    ),
    CreativeWork(
        identifiers=[WorkIdentifier(2)],
        agent_relations=[
            Host(agent=Person(4, name='Bill Lumbergh'), cited_as='Bill Lumbergh'),
            Funder(agent=Person(name='Bill Gates')),
            Publisher(agent=Person(6)),
        ]
    ),
    CreativeWork(
        identifiers=[WorkIdentifier(2)],
        related_agents=[
            Person(),
            Person(name='Laura Gates'),
            Person(),
        ]
    ),
    Publication(
        identifiers=[WorkIdentifier(3)],
        agent_relations=[
            Creator(agent=Person(7, identifiers=[AgentIdentifier(1)]))
        ],
        related_works=[
            Patent(
                agent_relations=[
                    Contributor(agent=Person(8, identifiers=[AgentIdentifier(2)]))
                ],
                identifiers=[WorkIdentifier(4)]
            )
        ]
    ),
]


@pytest.mark.django_db
class TestPersonDisambiguation:

    @pytest.mark.parametrize('input, model, delta', [
        ([Person(name='Bob Dylan')], models.Person, 1),
        ([Person(7, identifiers=[AgentIdentifier(1)])], models.Person, 0),
        ([Publication(identifiers=[WorkIdentifier(2)], agent_relations=[AgentWorkRelation(agent=Person(4, name='Bill Lumbergh'), cited_as='Bill Lumbergh')])], models.Person, 0),
        ([Publication(identifiers=[WorkIdentifier(2)], related_agents=[Person(9)])], models.Person, 1),
        ([CreativeWork(related_agents=[Person(name='Bill Gates')])], models.Person, 1),
        ([Preprint(related_agents=[Person(8, identifiers=[AgentIdentifier(2)])])], models.Person, 0),
    ])
    def test_disambiguate(self, input, model, delta, Graph):
        initial_cg = ChangeGraph(Graph(*initial))
        initial_cg.process(disambiguate=False)
        ChangeSet.objects.from_graph(initial_cg, NormalizedDataFactory().id).accept()

        Graph.reseed()
        # Nasty hack to avoid progres' fuzzy counting
        before = model.objects.exclude(change=None).exact_count()

        cg = ChangeGraph(Graph(*input))
        cg.process()
        cs = ChangeSet.objects.from_graph(cg, NormalizedDataFactory().id)
        if cs is not None:
            cs.accept()

        assert (model.objects.exclude(change=None).exact_count() - before) == delta

    @pytest.mark.parametrize('input', [
        [Person(identifiers=[AgentIdentifier()])],
        [Person(identifiers=[AgentIdentifier()]), Person(identifiers=[AgentIdentifier()])],
        [Publication(identifiers=[WorkIdentifier()], agent_relations=[Funder(agent=Person()), Publisher(agent=Person())])],
        [Preprint(identifiers=[WorkIdentifier()], related_agents=[Person(), Person()], agent_relations=[Funder(agent=Person()), Publisher(agent=Person())])]
    ])
    def test_reaccept(self, input, Graph):
        initial_cg = ChangeGraph(Graph(*initial))
        initial_cg.process()
        ChangeSet.objects.from_graph(initial_cg, NormalizedDataFactory().id).accept()

        Graph.reseed()  # Force new values to be generated

        first_cg = ChangeGraph(Graph(*input))
        first_cg.process()
        first_cs = ChangeSet.objects.from_graph(first_cg, NormalizedDataFactory().id)
        assert first_cs is not None
        first_cs.accept()

        second_cg = ChangeGraph(Graph(*input))
        second_cg.process()
        second_cs = ChangeSet.objects.from_graph(second_cg, NormalizedDataFactory().id)
        assert second_cs is None

    def test_no_changes(self, Graph):
        initial_cg = ChangeGraph(Graph(*initial))
        initial_cg.process()
        ChangeSet.objects.from_graph(initial_cg, NormalizedDataFactory().id).accept()

        Graph.discarded_ids.clear()
        cg = ChangeGraph(Graph(*initial))
        cg.process()
        assert ChangeSet.objects.from_graph(cg, NormalizedDataFactory().id) is None
