import pytest

from share import models
from share.change import ChangeGraph
from share.exceptions import MergeRequired
from share.models import ChangeSet

from tests import factories
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
        # creativework with same identifier as creativework and other identifiers
        ([CreativeWork(identifiers=[WorkIdentifier(3), WorkIdentifier(), WorkIdentifier()])], models.CreativeWork, 0),
        # creativework with same identifier as publication
        ([CreativeWork(identifiers=[WorkIdentifier(5)])], models.CreativeWork, 0),
        ([CreativeWork(identifiers=[WorkIdentifier(5)])], models.Publication, 0),
        # creativework with an additional identifier
        ([CreativeWork(identifiers=[WorkIdentifier(), WorkIdentifier(5)])], models.Publication, 0),
        ([CreativeWork(identifiers=[WorkIdentifier(), WorkIdentifier(5)])], models.WorkIdentifier, 1),
        ([CreativeWork(identifiers=[WorkIdentifier(20), WorkIdentifier(5)])], models.Publication, 0),
        ([CreativeWork(identifiers=[WorkIdentifier(21), WorkIdentifier(5)])], models.WorkIdentifier, 1),
        ([CreativeWork(identifiers=[WorkIdentifier(5), WorkIdentifier(22)])], models.Publication, 0),
        ([CreativeWork(identifiers=[WorkIdentifier(5), WorkIdentifier(23)])], models.WorkIdentifier, 1),
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

        # Graph.reseed()  # Force new values to be generated

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

    def test_split_brain(self, Graph):
        initial_cg = ChangeGraph(Graph(*initial))
        initial_cg.process()
        ChangeSet.objects.from_graph(initial_cg, NormalizedDataFactory().id).accept()

        # Multiple matches found for a thing should break
        cg = ChangeGraph(Graph(Preprint(identifiers=[WorkIdentifier(1), WorkIdentifier(2)])))
        with pytest.raises(MergeRequired) as e:
            cg.process()
        assert e.value.args[0] == "Multiple <class 'share.models.creative.Preprint'>s found"

    def test_no_merge_on_blank_value(self, Graph):
        blank_cited_as = [
            Publication(
                identifiers=[WorkIdentifier(1)],
                agent_relations=[
                    Publisher(cited_as='', agent=Organization(1)),
                ]
            )
        ]
        initial_cg = ChangeGraph(Graph(*blank_cited_as))
        initial_cg.process()
        ChangeSet.objects.from_graph(initial_cg, NormalizedDataFactory().id).accept()
        assert models.Publication.objects.count() == 1
        assert models.Publisher.objects.count() == 1
        assert models.Organization.objects.count() == 1

        additional_pub = [
            Publication(
                identifiers=[WorkIdentifier(1)],
                agent_relations=[
                    Publisher(cited_as='', agent=Organization(1)),
                    Publisher(cited_as='', agent=Organization(2)),
                ]
            )
        ]

        next_cg = ChangeGraph(Graph(*additional_pub))
        next_cg.process()
        ChangeSet.objects.from_graph(next_cg, NormalizedDataFactory().id).accept()
        assert models.Publication.objects.count() == 1
        assert models.Publisher.objects.count() == 2
        assert models.Organization.objects.count() == 2

    def test_no_timetraveling(self, Graph):
        newer_graph = ChangeGraph(Graph(
            Publication(
                id=1,
                sparse=True,
                identifiers=[WorkIdentifier(1)],
                date_updated='2017-02-03T18:07:53.385000',
                is_deleted=False,
            )
        ))

        newer_graph.process()
        ChangeSet.objects.from_graph(newer_graph, NormalizedDataFactory().id).accept()

        older_graph = ChangeGraph(Graph(
            Publication(
                id=1,
                sparse=True,
                identifiers=[WorkIdentifier(1)],
                date_updated='2017-02-03T18:07:50.000000',
                is_deleted=True,
                title='Not Previously Changed'
            )
        ))

        older_graph.process()
        assert older_graph.nodes[0].change == {'title': 'Not Previously Changed'}

    def test_no_timetraveling_many(self, Graph):
        oldest_graph = ChangeGraph(Graph(
            Publication(
                id=1,
                sparse=True,
                is_deleted=True,
                title='The first title',
                description='The first description',
                identifiers=[WorkIdentifier(1)],
                date_updated='2016-02-03T18:07:50.000000',
            )
        ))

        oldest_graph.process()
        ChangeSet.objects.from_graph(oldest_graph, NormalizedDataFactory().id).accept()

        newer_graph = ChangeGraph(Graph(
            Publication(
                id=1,
                sparse=True,
                is_deleted=False,
                identifiers=[WorkIdentifier(1)],
                date_updated='2017-02-03T18:07:50.000000',
            )
        ))

        newer_graph.process()
        ChangeSet.objects.from_graph(newer_graph, NormalizedDataFactory().id).accept()

        newest_graph = ChangeGraph(Graph(
            Publication(
                id=1,
                sparse=True,
                title='The final title',
                identifiers=[WorkIdentifier(1)],
                date_updated='2017-02-03T18:07:53.385000',
            )
        ))

        newest_graph.process()
        ChangeSet.objects.from_graph(newest_graph, NormalizedDataFactory().id).accept()

        older_graph = ChangeGraph(Graph(
            Publication(
                id=1,
                sparse=True,
                is_deleted=True,
                title='The second title',
                description='The final description',
                identifiers=[WorkIdentifier(1)],
                date_updated='2017-01-01T18:00:00.000000',
            )
        ))

        older_graph.process()
        assert older_graph.nodes[0].change == {'description': 'The final description'}

    @pytest.mark.parametrize('first_canonical, second_canonical, change', [
        (True, False, {}),
        (True, True, {'type': 'share.article', 'title': 'The Second Title'}),
        (False, True, {'type': 'share.article', 'title': 'The Second Title'}),
        (False, False, {'type': 'share.article', 'title': 'The Second Title'}),
    ])
    def test_canonical(self, Graph, first_canonical, second_canonical, change):
        first_source = factories.SourceFactory(canonical=first_canonical)
        second_source = factories.SourceFactory(canonical=second_canonical)

        first_graph = ChangeGraph(Graph(
            Preprint(
                id=1,
                title='The first title',
                identifiers=[WorkIdentifier(1)],
            )
        ), namespace=first_source.user.username)

        second_graph = ChangeGraph(Graph(
            Article(
                id=1,
                title='The Second Title',
                identifiers=[WorkIdentifier(1)],
            )
        ), namespace=second_source.user.username)

        first_graph.process()
        (cw, _) = ChangeSet.objects.from_graph(first_graph, NormalizedDataFactory(source=first_source.user).id).accept()

        assert cw.type == 'share.preprint'
        assert cw.title == 'The first title'

        second_graph.process()
        ChangeSet.objects.from_graph(second_graph, NormalizedDataFactory(source=second_source.user).id).accept()

        cw = models.AbstractCreativeWork.objects.get(id=cw.id)

        assert second_graph.nodes[0].change == change
        assert cw.type == change.get('type', 'share.preprint')
        assert cw.title == change.get('title', 'The first title')
