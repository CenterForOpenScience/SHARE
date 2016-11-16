# flake8: noqa
from share import models
from tests.share.normalize.factories import *


class TestShortHand:

    def test_id(self):
        assert Agent(0) == {'seed': 0, 'type': 'agent'}
        assert Person(0) == {'seed': 0, 'type': 'person'}
        assert Organization(0) == {'seed': 0, 'type': 'organization'}
        assert Institution(0) == {'seed': 0, 'type': 'institution'}

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
            'identifiers': [{'seed': 0, 'type': 'workidentifier'}, {'seed': 1, 'type': 'workidentifier'}],
            'related_works': [{
                'type': 'preprint',
                'identifiers': [{'seed': 0, 'type': 'workidentifier'}]
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

    def test_cross_graph_identity(self, Graph):
        assert Graph(CreativeWork(0))[0] == Graph(CreativeWork(0))[0]

    def test_nested(self, Graph):
        graph = Graph(CreativeWork(identifiers=[WorkIdentifier()]))

        work = next(x for x in graph if x['@type'] == 'creativework')
        identifier = next(x for x in graph if x['@type'] == 'workidentifier')

        assert len(graph) == 2
        assert identifier['creative_work']['@id'] == work['@id']
        assert identifier['creative_work']['@type'] == work['@type']
        assert 'identifiers' not in work

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

    def test_type_out_of_order(self, Graph):
        assert Graph(Tag(), CreativeWork(), Tag()) == Graph(CreativeWork(), Tag(), Tag())

    def test_ids_dont_effect(self, Graph):
        assert Graph(Tag(), Tag(1, id=1), Tag()) == Graph(Tag(), Tag(), Tag(1, id=1))

    def test_cases(self, Graph):
        assert Graph(AgentIdentifier(1), AgentIdentifier(1), AgentIdentifier(1)) == Graph(AgentIdentifier(1), AgentIdentifier(1), AgentIdentifier(1))
        assert Graph(AgentIdentifier(seed=1), AgentIdentifier(seed=1), AgentIdentifier(seed=1)) == Graph(AgentIdentifier(seed=1), AgentIdentifier(seed=1), AgentIdentifier(seed=1))

        data = Graph(
            Person(0, name='Barb Dylan', identifiers=[AgentIdentifier(seed=1)]),
            Person(1, name='Barb Dylan', identifiers=[AgentIdentifier(seed=1)]),
            Person(2, name='Barb Dylan', identifiers=[AgentIdentifier(seed=1)])
        )
        assert len(data) == 6

        assert data == Graph(
            Person(0, name='Barb Dylan', identifiers=[AgentIdentifier(seed=1)]),
            Person(1, name='Barb Dylan', identifiers=[AgentIdentifier(seed=1)]),
            Person(2, name='Barb Dylan', identifiers=[AgentIdentifier(seed=1)])
        )

        Graph.discarded_ids.add(next(x['@id'] for x in data if x['@type'] == 'agentidentifier'))

        assert Graph(Person(0, name='Barb Dylan', identifiers=[AgentIdentifier(seed=1)]))[0] in data

        assert Graph(Person(0, name='Barb Dylan', identifiers=[AgentIdentifier(seed=1)]))[1] in data

        identifiers = list(x for x in data if x['@type'] == 'agentidentifier')
        assert len(identifiers) == 3
        assert len(set(i['@id'] for i in identifiers)) == 3

        for i in identifiers:
            i = {**i}
            i.pop('@id')
            i['agent'].pop('@id', None)
            for j in identifiers:
                j = {**j}
                j.pop('@id')
                j['agent'].pop('@id', None)
                assert i == j

