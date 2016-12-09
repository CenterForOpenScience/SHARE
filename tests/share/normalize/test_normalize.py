import pytest

import pendulum

from share import models
from share.change import ChangeGraph
from share.util import IDObfuscator, InvalidID

from tests.share.models import factories


class TestGraph:

    def test_create(self, graph):
        assert len(graph.nodes) == 0  # Nothing up my sleeve

        node = graph.create(None, 'tag', {'name': 'Foo'})

        assert len(graph.nodes) == 1
        assert graph.nodes == [node]
        assert graph.get(node.id, node.type) is node
        assert node.graph is graph
        assert graph.nodes[0] is node
        assert graph.nodes[0].type == 'tag'
        assert graph.nodes[0].model == models.Tag
        assert graph.nodes[0].attrs == {'name': 'Foo'}
        assert graph.nodes[0].related() == tuple()
        assert graph.nodes[0].is_blank is True
        assert graph.nodes[0].id is not None

    def test_create_extra(self):
        graph = ChangeGraph([], namespace='testing')
        node = graph.create(None, 'tag', {'name': 'Foo', 'extra': {'tag': 'Foo'}})
        assert node.namespace == 'testing'

    def test_create_id(self, graph):
        node = graph.create('_:something', 'tag', {'name': 'Foo'})

        assert len(graph.nodes) == 1
        assert graph.get('_:something', 'tag') is node
        assert node.attrs == {'name': 'Foo'}
        assert node.id is '_:something'
        assert node.is_blank is True
        assert node.model == models.Tag
        assert node.related() == ()
        assert node.type == 'tag'

    def test_create_many(self, graph):
        for _ in range(10):
            graph.create(None, 'WorkIdentifier', {'uri': 'https://google.com'})

        assert len(graph.nodes) == 10

    def test_create_many_id(self, graph):
        for i in range(10):
            graph.create('_:{}'.format(i), 'Tag', {'name': 'Tag number {}'.format(i)})

        assert len(graph.nodes) == 10

        for i in range(10):
            assert graph.get('_:{}'.format(i), 'tag').attrs['name'] == 'Tag number {}'.format(i)

    def test_relate(self, graph):
        tag = graph.create(None, 'tag', {})
        throughtag = graph.create(None, 'throughtags', {})

        edge = graph.relate(throughtag, tag)

        assert edge.subject == throughtag
        assert edge.related == tag
        assert tag.related() == (edge, )
        assert throughtag.related() == (edge, )

    def test_remove(self, graph):
        node = graph.create(None, 'tag', {})
        graph.remove(node)
        assert len(graph.nodes) == 0

    def test_remove_many(self, graph):
        for i in range(10):
            graph.create('_:{}'.format(i), 'tag', {})

        assert len(graph.nodes) == 10

        for i in range(0, 10, -1):
            graph.remove(graph.get('_:{}'.format(i), 'tag'))
            assert len(graph.nodes) == i

    def test_remove_cascade(self, graph):
        tag = graph.create(None, 'tag', {})
        throughtag = graph.create(None, 'throughtags', {})
        graph.relate(throughtag, tag)

        assert len(graph.nodes) == 2
        assert len(graph.relations) == 2

        graph.remove(tag)

        assert len(graph.nodes) == 0
        assert len(graph.relations) == 0

    def test_remove_no_cascade_backwards(self, graph):
        tag = graph.create(None, 'tag', {})
        throughtag = graph.create(None, 'throughtags', {})
        graph.relate(throughtag, tag)

        assert len(graph.nodes) == 2
        assert len(graph.relations) == 2

        graph.remove(throughtag)

        assert graph.nodes == [tag]
        assert tag.related() == tuple()
        assert len(graph.relations) == 1

    def test_replace(self, graph):
        tag1 = graph.create(None, 'tag', {})
        tag2 = graph.create(None, 'tag', {})
        throughtag = graph.create(None, 'throughtags', {})
        graph.relate(throughtag, tag1)

        graph.replace(tag1, tag2)

        assert set(graph.nodes) == set([throughtag, tag2])
        assert throughtag.related('tag').related is tag2


class TestChangeNode:

    def test_related(self, graph):
        tag = graph.create(None, 'tag', {})
        throughtag = graph.create(None, 'throughtags', {})
        creative_work = graph.create(None, 'creativework', {})

        graph.relate(throughtag, tag)
        graph.relate(throughtag, creative_work)

        assert len(throughtag.related()) == 2
        assert set(e.related for e in throughtag.related()) == {tag, creative_work}

        assert len(creative_work.related()) == 1
        assert set(e.subject for e in throughtag.related()) == {throughtag}

        assert len(tag.related()) == 1
        assert set(e.subject for e in tag.related()) == {throughtag}

    def test_related_forward(self, graph):
        tag = graph.create(None, 'tag', {})
        throughtag = graph.create(None, 'throughtags', {})
        creative_work = graph.create(None, 'creativework', {})

        graph.relate(throughtag, tag)
        graph.relate(throughtag, creative_work)

        assert throughtag.related('tag').related is tag
        assert throughtag.related('creative_work').related is creative_work

        assert len(tag.related(backward=False)) == 0
        assert len(throughtag.related(backward=False)) == 2
        assert len(creative_work.related(backward=False)) == 0
        assert set(e.related for e in throughtag.related(backward=False)) == {tag, creative_work}

    def test_related_backward(self, graph):
        tag = graph.create(None, 'tag', {})
        throughtag = graph.create(None, 'throughtags', {})
        creative_work = graph.create(None, 'creativework', {})

        graph.relate(throughtag, tag)
        graph.relate(throughtag, creative_work)

        assert len(tag.related(forward=False)) == 1
        assert len(throughtag.related(forward=False)) == 0
        assert len(creative_work.related(forward=False)) == 1

        assert set(e.subject for e in tag.related(forward=False)) == {throughtag}
        assert set(e.subject for e in creative_work.related(forward=False)) == {throughtag}

    def test_related_name(self, graph):
        tag1 = graph.create(None, 'tag', {})
        tag2 = graph.create(None, 'tag', {})
        throughtag1 = graph.create(None, 'throughtags', {})
        throughtag2 = graph.create(None, 'throughtags', {})
        creative_work = graph.create(None, 'creativework', {})

        graph.relate(throughtag1, tag1)
        graph.relate(throughtag2, tag2)
        graph.relate(throughtag1, creative_work)
        graph.relate(throughtag2, creative_work)

        assert set(e.subject for e in tag1.related('work_relations')) == {throughtag1}
        assert set(e.subject for e in tag2.related('work_relations')) == {throughtag2}
        assert set(e.subject for e in creative_work.related('tag_relations')) == {throughtag1, throughtag2}

    @pytest.mark.skip
    def test_related_reverse_name(self):
        pass

    @pytest.mark.skip
    def test_related_multiple_found(self):
        pass

    @pytest.mark.skip
    def test_related_multiple(self):
        pass

    @pytest.mark.django_db
    def test_load_instance(self, graph):
        tag = factories.TagFactory()
        assert graph.create(IDObfuscator.encode(tag), 'tag', {}).instance == tag

    @pytest.mark.django_db
    def test_unresolveable(self, graph):
        with pytest.raises(InvalidID) as e:
            graph.create('Foo', 'tag', {'name': 'Not a generated Value'})
        assert e.value.args == ('Foo', 'Not a valid ID')

    @pytest.mark.django_db
    def test_change_no_diff(self, graph):
        tag = factories.TagFactory()
        assert graph.create(IDObfuscator.encode(tag), 'tag', {'name': tag.name}).change == {}

    @pytest.mark.django_db
    def test_change_diff(self, graph):
        tag = factories.TagFactory(name='tag1')
        assert graph.create(IDObfuscator.encode(tag), 'tag', {'name': 'tag2'}).change == {'name': 'tag2'}

    @pytest.mark.django_db
    def test_change_datetime_no_change(self, graph):
        work = factories.AbstractCreativeWorkFactory()
        assert graph.create(IDObfuscator.encode(work), work._meta.model_name, {'date_updated': work.date_updated.isoformat()}).change == {}

    @pytest.mark.django_db
    def test_change_datetime_change(self, graph):
        tag = factories.AbstractCreativeWorkFactory()
        assert graph.create(IDObfuscator.encode(tag), 'tag', {'date_updated': pendulum.fromtimestamp(0).isoformat()}).change == {'date_updated': pendulum.fromtimestamp(0).isoformat()}

    @pytest.mark.django_db
    def test_change_extra(self, graph):
        tag_model = factories.AbstractCreativeWorkFactory(extra=models.ExtraData.objects.create(
            change=factories.ChangeFactory(),
            data={'testing': {
                'Same': 'here',
                'Overwrite': 'me',
                'Dont touch': 'this one',
            }}
        ))
        graph.namespace = 'testing'
        tag = graph.create(None, 'tag', {'extra': {'Same': 'here', 'Overwrite': 'you', 'New key': 'here'}})
        tag.instance = tag_model
        assert tag.change == {'extra': {
            'New key': 'here',
            'Overwrite': 'you',
        }}

    def test_extra(self, graph):
        graph.namespace = 'testing'
        tag = graph.create(None, 'tag', {'extra': {'Additional': 'data'}})
        assert tag.change == {'extra': {'Additional': 'data'}}
