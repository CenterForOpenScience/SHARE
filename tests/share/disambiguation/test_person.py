import pytest

from share import models

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

    @pytest.fixture
    def ingest_initial(self, Graph, ingest):
        ingest(Graph(initial))

    @pytest.mark.parametrize('input, model, delta', [
        ([Person(name='Bob Dylan')], models.Person, 1),
        ([Person(7, identifiers=[AgentIdentifier(1)])], models.Person, 0),
        ([Publication(identifiers=[WorkIdentifier(2)], agent_relations=[AgentWorkRelation(agent=Person(4, name='Bill Lumbergh'), cited_as='Bill Lumbergh')])], models.Person, 0),
        ([Publication(identifiers=[WorkIdentifier(2)], related_agents=[Person(9)])], models.Person, 1),
        ([CreativeWork(related_agents=[Person(name='Bill Gates')])], models.Person, 1),
        ([Preprint(related_agents=[Person(8, identifiers=[AgentIdentifier(2)])])], models.Person, 0),
    ])
    def test_disambiguate(self, input, model, delta, Graph, ingest_initial, ingest):
        Graph.reseed()
        # Nasty hack to avoid progres' fuzzy counting
        before = model.objects.exclude(change=None).count()

        ingest(Graph(input))

        assert (model.objects.exclude(change=None).count() - before) == delta

    @pytest.mark.parametrize('input', [
        [Person(identifiers=[AgentIdentifier()])],
        [Person(identifiers=[AgentIdentifier()]), Person(identifiers=[AgentIdentifier()])],
        [Publication(identifiers=[WorkIdentifier()], agent_relations=[Funder(agent=Person()), Publisher(agent=Person())])],
        [Preprint(identifiers=[WorkIdentifier()], related_agents=[Person(), Person()], agent_relations=[Funder(agent=Person()), Publisher(agent=Person())])]
    ])
    def test_reaccept(self, input, Graph, ingest_initial, ingest):
        Graph.reseed()  # Force new values to be generated

        first_cs = ingest(Graph(input))
        assert first_cs is not None

        second_cs = ingest(Graph(input))
        assert second_cs is None

    def test_no_changes(self, Graph, ingest_initial, ingest):
        Graph.discarded_ids.clear()
        cs = ingest(Graph(initial))
        assert cs is None
