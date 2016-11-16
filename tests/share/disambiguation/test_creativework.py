import pytest

from share import models
from share.change import ChangeGraph
from share.models import ChangeSet

from tests.share.models.factories import NormalizedDataFactory
from tests.share.normalize.factories import *


initial = [
    Preprint(
        tags=[Tag(name=' Science')],
        identifiers=[WorkIdentifier(1)],
        related_agents=[
            Person(1),
            Person(2),
            Person(3),
            Institution(4),
        ],
        related_works=[
            Article(tags=[Tag(name='Science\n; Stuff')], identifiers=[WorkIdentifier(2)])
        ]
    ),
    CreativeWork(
        tags=[Tag(name='Ghosts N Stuff')],
        identifiers=[WorkIdentifier(3)],
        related_agents=[
            Person(5),
            Person(6),
            Person(7),
            Organization(8, name='Aperture Science'),
            Institution(9),
        ],
        related_works=[
            DataSet(identifiers=[WorkIdentifier(4)], related_agents=[Consortium(10)])
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
class TestWorkDisambiguation:

    @pytest.mark.parametrize('input, model, delta', [
        # creativework with different identifier as creativework
        ([CreativeWork(identifiers=[WorkIdentifier(7)])], models.CreativeWork, 1),
        # creativework with same identifier as creativework
        ([CreativeWork(identifiers=[WorkIdentifier(3)])], models.CreativeWork, 0),
        # creativework with same identifier as publication
        ([CreativeWork(identifiers=[WorkIdentifier(5)])], models.CreativeWork, 0),
        ([CreativeWork(identifiers=[WorkIdentifier(5)])], models.Publication, 0),
        # article with same identifier as publication
        ([Article(identifiers=[WorkIdentifier(5)])], models.Article, 1),
        ([Article(identifiers=[WorkIdentifier(5)])], models.Publication, 0),
        # software with same identifier as dataset (same level)
        # fails
        ([Software(identifiers=[WorkIdentifier(4)])], models.Software, 1),
        ([Software(identifiers=[WorkIdentifier(4)])], models.DataSet, -1),
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
        [Publication(identifiers=[WorkIdentifier()])],
        [CreativeWork(identifiers=[WorkIdentifier()])],
        [Software(identifiers=[WorkIdentifier()])],
        [Article(identifiers=[WorkIdentifier()])],
        [Thesis(identifiers=[WorkIdentifier()])],
        [Preprint(identifiers=[WorkIdentifier()], related_agents=[Person(), Consortium()], agent_relations=[Funder(), Publisher()])]
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