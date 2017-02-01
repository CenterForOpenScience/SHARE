import pytest

from share import models
from share.change import ChangeGraph
from share.models import ChangeSet
from share.util import IDObfuscator

from tests.share.models.factories import NormalizedDataFactory
from tests.share.normalize.factories import *


initial_works = [
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


def setup(Graph, filter_type=models.CreativeWork):
    works = []
    for initial in initial_works:
        initial_cg = ChangeGraph(Graph(initial))
        initial_cg.process()
        objs = ChangeSet.objects.from_graph(initial_cg, NormalizedDataFactory().id).accept()
        works.append(next(o for o in objs if isinstance(o, filter_type)))
    return works


def merge_node(from_obj, into_obj):
    return {
        '@id': IDObfuscator.encode(from_obj),
        '@type': from_obj._meta.model_name,
        'same_as': {'@id': IDObfuscator.encode(into_obj), '@type': into_obj._meta.model_name}
    }


def work_snapshot(work):
    # refresh from DB, even if type has changed
    work = work._meta.concrete_model.objects.get(id=work.id)
    attributes = {
        f.name: getattr(work, f.name)
        for f in work._meta.get_fields()
        if f.editable and not f.is_relation and not f.primary_key
    }
    return {
        **attributes,
        'tags': {t.name for t in work.tags.all()},
        'identifiers': {i.uri for i in work.identifiers.all()},
        'related_agents': {(r.type, r.agent.name) for r in work.agent_relations.all()},
        'incoming_related_works': {(r.type, r.subject.title) for r in work.incoming_creative_work_relations.all()},
        'outgoing_related_works': {(r.type, r.related.title) for r in work.outgoing_creative_work_relations.all()},
    }


def agent_snapshot(agent):
    # refresh from DB, even if type has changed
    agent = agent._meta.concrete_model.objects.get(id=agent.id)
    attributes = {
        f.name: getattr(agent, f.name)
        for f in agent._meta.get_fields()
        if f.editable and not f.is_relation and not f.primary_key
    }
    return {
        **attributes,
        'identifiers': {i.uri for i in agent.identifiers.all()},
        'related_works': {(r.type, r.creative_work.title) for r in agent.work_relations.all()},
        'incoming_related_agents': {(r.type, r.subject.title) for r in agent.incoming_agent_relations.all()},
        'outgoing_related_agents': {(r.type, r.related.title) for r in agent.outgoing_agent_relations.all()},
    }


def merge_snapshots(older, newer):
    merged = {}
    for k, v in newer.items():
        if isinstance(v, set):
            merged[k] = v | older[k]
        else:
            merged[k] = v if v else older[k]
    return merged


@pytest.mark.django_db
class TestMergingObjects:
    def test_merge_two_works(self, Graph):
        from_work, into_work = setup(Graph)[:2]
        from_snapshot = work_snapshot(from_work)
        into_snapshot = work_snapshot(into_work)

        merge_cg = ChangeGraph([merge_node(from_work, into_work)])
        merge_cg.process()
        ChangeSet.objects.from_graph(merge_cg, NormalizedDataFactory().id).accept()

        from_work.refresh_from_db()
        assert from_work.same_as_id == into_work.id
        assert merge_snapshots(from_snapshot, into_snapshot) == work_snapshot(into_work)

    def test_merge_two_works_reverse(self, Graph):
        into_work, from_work = setup(Graph)[:2]
        from_snapshot = work_snapshot(from_work)
        into_snapshot = work_snapshot(into_work)

        merge_cg = ChangeGraph([merge_node(from_work, into_work)])
        merge_cg.process()
        ChangeSet.objects.from_graph(merge_cg, NormalizedDataFactory().id).accept()

        from_work.refresh_from_db()
        assert from_work.same_as_id == into_work.id
        assert merge_snapshots(into_snapshot, from_snapshot) == work_snapshot(into_work)

    def test_merge_several_works(self, Graph):
        *from_works, into_work = setup(Graph)
        from_snapshots = [work_snapshot(w) for w in from_works]
        into_snapshot = work_snapshot(into_work)

        merge_cg = ChangeGraph([merge_node(w, into_work) for w in from_works])
        merge_cg.process()
        ChangeSet.objects.from_graph(merge_cg, NormalizedDataFactory().id).accept()

        for from_work in from_works:
            from_work.refresh_from_db()
            assert from_work.same_as_id == into_work.id

        merged_snapshot = into_snapshot
        for snapshot in from_snapshots:
            merged_snapshot = merge_snapshots(snapshot, merged_snapshot)
        assert merged_snapshot == work_snapshot(into_work)

    def test_implicitly_merge_two_works(self, Graph):
        from_work, into_work = setup(Graph)[:2]
        from_snapshot = work_snapshot(from_work)
        into_snapshot = work_snapshot(into_work)

        merge_cg = ChangeGraph(Graph(
            CreativeWork(
                sparse=True,
                id='_:foo',
                identifiers=[
                    WorkIdentifier(uri=from_work.identifiers.first().uri),
                    WorkIdentifier(uri=into_work.identifiers.first().uri),
                ]
            )
        ))
        merge_cg.process()
        ChangeSet.objects.from_graph(merge_cg, NormalizedDataFactory().id).accept()

        from_work.refresh_from_db()
        assert from_work.same_as_id == into_work.id
        merged_snapshot = merge_snapshots(from_snapshot, into_snapshot)
        assert merged_snapshot == work_snapshot(into_work)

    def test_implicitly_merge_several_works(self, Graph):
        works = setup(Graph)
        snapshots = [work_snapshot(w) for w in works]

        merge_cg = ChangeGraph(Graph(
            CreativeWork(
                sparse=True,
                id='_:foo',
                identifiers=[
                    WorkIdentifier(uri=w.identifiers.first().uri) for w in works
                ]
            )
        ))
        merge_cg.process()
        ChangeSet.objects.from_graph(merge_cg, NormalizedDataFactory().id).accept()

        into_work = works.pop()
        for from_work in works:
            from_work.refresh_from_db()
            assert from_work.same_as_id == into_work.id

        merged_snapshot = snapshots.pop(0)
        for snapshot in snapshots:
            merged_snapshot = merge_snapshots(merged_snapshot, snapshot)
        assert merged_snapshot == work_snapshot(into_work)

    def test_merge_agents(self, Graph):
        from_agent, into_agent = setup(Graph, filter_type=models.Agent)[:2]
        from_snapshot = agent_snapshot(from_agent)
        into_snapshot = agent_snapshot(into_agent)

        merge_cg = ChangeGraph([merge_node(from_agent, into_agent)])
        merge_cg.process()
        ChangeSet.objects.from_graph(merge_cg, NormalizedDataFactory().id).accept()

        from_agent.refresh_from_db()
        assert from_agent.same_as_id == into_agent.id
        assert merge_snapshots(from_snapshot, into_snapshot) == agent_snapshot(into_agent)

    def test_update_in_merge_node_fails(self, Graph):
        from_work, into_work = setup(Graph)[:2]
        m = merge_node(from_work, into_work)
        m['title'] = 'updated title!'
        merge_cg = ChangeGraph([m])
        merge_cg.process()
        with pytest.raises(AssertionError):
            ChangeSet.objects.from_graph(merge_cg, NormalizedDataFactory().id).accept()
