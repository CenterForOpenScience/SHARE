# flake8: noqa
from share import models
from tests.share.normalize.factories import *


class TestShortHand:

    def test_id(self):
        assert Agent(0) == {'id': 0, 'type': 'agent'}
        assert Person(0) == {'id': 0, 'type': 'person'}
        assert Organization(0) == {'id': 0, 'type': 'organization'}
        assert Institution(0) == {'id': 0, 'type': 'institution'}

    def test_anon(self):
        assert CreativeWork() == {'type': 'creativework'}
        assert Article() == {'type': 'article'}
        assert Publication() == {'type': 'publication'}
        assert Patent() == {'type': 'patent'}

    def test_kwargs(self):
        kwargs = {'hello': 'World'}
        assert CreativeWork(**kwargs) == {'type': 'creativework', **kwargs}
        assert Article(**kwargs) == {'type': 'article', **kwargs}
        assert Publication(**kwargs) == {'type': 'publication', **kwargs}
        assert Patent(**kwargs) == {'type': 'patent', **kwargs}

    def test_nesting(self):
        assert CreativeWork(
            identifiers=[WorkIdentifier(0), WorkIdentifier(1)],
            related_works=[Preprint(identifiers=[WorkIdentifier(0)])]
        ) == {
            'type': 'creativework',
            'identifiers': [{'id': 0, 'type': 'workidentifier'}, {'id': 1, 'type': 'workidentifier'}],
            'related_works': [{
                'type': 'preprint',
                'identifiers': [{'id': 0, 'type': 'workidentifier'}]
            }]
        }

class TestMakeGraph:

    def test_single_node(self, Graph):
        graph = Graph(
            CreativeWork(name='Foo')
        )
        assert isinstance(graph, list)
        assert len(graph) == 1
        assert graph[0]['name'] == 'Foo'
        assert graph[0]['@type'] == 'creativework'
        assert graph[0]['@id'].startswith('_:')

    def test_multiple_nodes(self, Graph):
        graph = Graph(
            CreativeWork(name='Foo'),
            Tag(name='Bar'),
        )

        assert len(graph) == 2

        tag = next(x for x in graph if x['@type'] == 'tag')
        work = next(x for x in graph if x['@type'] == 'creativework')

        assert work['name'] == 'Foo'
        assert work['@type'] == 'creativework'
        assert work['@id'].startswith('_:')
        assert tag['name'] == 'Bar'
        assert tag['@type'] == 'tag'
        assert tag['@id'].startswith('_:')

    # def test_identity(self, Graph):
    #     graph = Graph(CreativeWork(0), CreativeWork(0))

    #     assert graph[0] is graph[1]

    def test_cross_graph_identity(self, Graph):
        assert Graph(CreativeWork(0))[0] is Graph(CreativeWork(0))[0]

    def test_nested(self, Graph):
        graph = Graph(CreativeWork(identifiers=[WorkIdentifier()]))

        work = next(x for x in graph if x['@type'] == 'creativework')
        identifier = next(x for x in graph if x['@type'] == 'workidentifier')

        assert len(graph) == 2
        assert identifier['creative_work']['@id'] == work['@id']
        assert identifier['creative_work']['@type'] == work['@type']
        assert work['identifiers'][0]['@id'] == identifier['@id']
        assert work['identifiers'][0]['@type'] == identifier['@type']

    def test_many_to_many(self, Graph):
        graph = Graph(CreativeWork(tags=[Tag()]))

        assert len(graph) == 3
        assert graph[0]['@type'] == 'creativework'
        assert graph[1]['@type'] == 'tag'
        assert graph[2]['@type'] == 'throughtags'

    def test_many_to_many_related(self, Graph):
        graph = Graph(CreativeWork(tag_relations=[ThroughTags()]))

        assert len(graph) == 3
        assert graph[0]['@type'] == 'creativework'
        assert graph[1]['@type'] == 'tag'
        assert graph[2]['@type'] == 'throughtags'

    def test_reseeds(self, Graph):
        assert Graph(CreativeWork()) == Graph(CreativeWork())

    def test_reseeds_many(self, Graph):
        assert Graph(CreativeWork(), CreativeWork(), CreativeWork(), Tag(), WorkIdentifier()) == Graph(CreativeWork(), CreativeWork(), CreativeWork(), Tag(), WorkIdentifier())
