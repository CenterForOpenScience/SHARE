import pytest

from share import models

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
    Report(
        identifiers=[WorkIdentifier(4)],
        agent_relations=[
            Creator(agent=Person(name='Berkeley')),
            Publisher(agent=Institution(name='Berkeley'))
        ]
    )
]


@pytest.mark.django_db
class TestAgentDisambiguation:

    @pytest.fixture
    def ingest_initial(self, ingest, Graph):
        ingest(Graph(initial))

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
        # organization and person exist with the same name
        ([Organization(name='Berkeley')], models.Organization, 0),
        # institution and person exist with the same name
        ([Institution(name='Berkeley')], models.Institution, 0),
        # person doesn't disambiguate on name
        ([Person(name='Berkeley')], models.Person, 1),
    ])
    def test_disambiguate(self, ingest_initial, ingest, input, model, delta, Graph):
        Graph.reseed()
        # Nasty hack to avoid progres' fuzzy counting
        before = model.objects.exclude(change=None).count()

        ingest(Graph(input))

        assert (model.objects.exclude(change=None).count() - before) == delta

    @pytest.mark.parametrize('input', [
        [Institution()],
        [Institution(name='Money Money')],
        [Organization(name='Money Makers'), Consortium()],
        [Institution(identifiers=[AgentIdentifier()])],
        [Publication(identifiers=[WorkIdentifier()], agent_relations=[Funder(agent=Organization()), Publisher(agent=Institution())])],
        [Preprint(identifiers=[WorkIdentifier()], related_agents=[Institution(), Organization()], agent_relations=[Funder(agent=Institution()), Publisher(agent=Organization())])]
    ])
    def test_reaccept(self, ingest_initial, ingest, input, Graph):
        Graph.reseed()  # Force new values to be generated

        first_cs = ingest(Graph(input))
        assert first_cs is not None

        second_cs = ingest(Graph(input))
        assert second_cs is None

    def test_no_changes(self, ingest, ingest_initial, normalized_data, Graph):
        Graph.discarded_ids.clear()
        cs = ingest(Graph(initial))
        assert cs is None
