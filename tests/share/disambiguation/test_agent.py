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
            Contributor(agent=Organization(1, name='American Heart Association')),
            Creator(agent=Organization(2)),
            Creator(agent=Organization(3)),
        ]
    ),
    CreativeWork(
        identifiers=[WorkIdentifier(2)],
        agent_relations=[
            Host(agent=Institution(4)),
            Funder(agent=Institution(name='NIH')),
            Publisher(agent=Institution(6)),
        ]
    ),
    CreativeWork(
        identifiers=[WorkIdentifier(2)],
        related_agents=[
            Institution(),
            Consortium(name='COS'),
            Organization(),
        ]
    ),
    Publication(
        identifiers=[WorkIdentifier(3)],
        agent_relations=[
            Creator(agent=Organization(7))
        ],
        related_works=[
            Patent(
                agent_relations=[
                    Contributor(agent=Institution(8))
                ],
                identifiers=[WorkIdentifier(4)]
            )
        ]
    ),
]


@pytest.mark.django_db
class TestAgentDisambiguation:

    @pytest.mark.parametrize('input, model, delta', [
        # institution with same name already exists
        ([Institution(name='NIH')], models.Institution, 0),
        # same organization already exists
        ([Organization(2)], models.Organization, 0),
        # same institution already exists
        ([Publication(related_agents=[Institution(4)])], models.Institution, 0),
        # consortium with same name already exists
        ([Publication(related_agents=[Consortium(name='COS')])], models.Consortium, 0),
        # institution already exists on a related work
        ([Preprint(related_agents=[Institution(8)])], models.Institution, 0),
        # organization where the name does not exist
        ([CreativeWork(related_agents=[Organization(name='Bill Gates')])], models.Organization, 1),
    ])
    def test_disambiguate(self, input, model, delta, Graph):
        initial_cg = ChangeGraph(Graph(*initial))
        initial_cg.process(disambiguate=False)
        ChangeSet.objects.from_graph(initial_cg, NormalizedDataFactory().id).accept()

        Graph.reseed()
        # Nasty hack to avoid progres' fuzzy counting
        before = model.objects.exclude(change=None).count()

        cg = ChangeGraph(Graph(*input))
        cg.process()
        cs = ChangeSet.objects.from_graph(cg, NormalizedDataFactory().id)
        if cs is not None:
            cs.accept()

        assert (model.objects.exclude(change=None).count() - before) == delta

    @pytest.mark.parametrize('input', [
        [Institution()],
        [Institution(name='Money Money')],
        [Organization(name='Money Makers'), Consortium()],
        [Institution(identifiers=[AgentIdentifier()])],
        [Publication(identifiers=[WorkIdentifier()], agent_relations=[Funder(agent=Organization()), Publisher(agent=Institution())])],
        [Preprint(identifiers=[WorkIdentifier()], related_agents=[Institution(), Organization()], agent_relations=[Funder(agent=Institution()), Publisher(agent=Organization())])]
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
