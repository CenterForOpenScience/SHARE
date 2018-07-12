import pytest

from share import models

from tests.share.normalize.factories import *


initial = [
    Preprint(
        tags=[Tag(name=' Science')],
        identifiers=[WorkIdentifier(1)],
        related_agents=[
            Person(),
            Person(),
            Person(),
            Institution(),
        ],
        related_works=[
            Article(tags=[Tag(name='Science\n; Stuff')], identifiers=[WorkIdentifier(2)])
        ]
    ),
    CreativeWork(
        tags=[Tag(name='Ghosts N Stuff')],
        identifiers=[WorkIdentifier(3)],
        related_agents=[
            Person(),
            Person(),
            Person(),
            Organization(name='Aperture Science'),
            Institution(),
        ],
        related_works=[
            DataSet(identifiers=[WorkIdentifier(4)], related_agents=[Consortium()])
        ]
    ),
    Publication(
        tags=[Tag(name=' Science')],
        identifiers=[WorkIdentifier(5)],
        related_agents=[Organization(name='Umbrella Corporation')],
        related_works=[
            Patent(
                tags=[Tag(name='Science\n; Stuff')],
                identifiers=[WorkIdentifier(6)]
            )
        ]
    ),
]


@pytest.mark.django_db
class TestDisambiguation:

    @pytest.fixture
    def ingest_initial(self, Graph, ingest):
        ingest(Graph(initial))

    @pytest.mark.parametrize('input, model, delta', [
        ([Tag(name='Science')], models.Tag, 0),
        ([Tag(name='Science; Things')], models.Tag, 1),
        ([Tag(name='SCIENCE'), Tag(name='Ghosts')], models.Tag, 1),
        ([Publication(identifiers=[WorkIdentifier(5)])], models.Publication, 0),
        ([Publication(identifiers=[WorkIdentifier(3)])], models.Publication, 1),
        ([Organization(name='Aperture Science')], models.Organization, 0),
        ([Organization(name='Aperture science')], models.Organization, 0),
    ])
    def test_disambiguate(self, input, model, delta, Graph, ingest_initial, ingest):
        Graph.reseed()
        # Nasty hack to avoid progres' fuzzy counting
        before = model.objects.exclude(change=None).count()

        ingest(Graph(input))

        assert (model.objects.exclude(change=None).count() - before) == delta

    @pytest.mark.parametrize('input', [
        [Tag(name='Not Ipsum')],
        [Tag(name='No Step'), Tag(name='On'), Tag(name='Snek')],
        [AgentIdentifier(), Organization(name='Team Snag \'em')],
        [Person(identifiers=[AgentIdentifier()])],
        [Publication(identifiers=[WorkIdentifier()])],
        [Preprint(identifiers=[WorkIdentifier()], related_agents=[Person(), Consortium()], agent_relations=[Funder(), Publisher()])]
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
