import pytest

from share.change import ChangeGraph
from share.change import UnresolvableReference
from share.util import CyclicalDependency


class TestChangeNode:

    def test_from_ld(self):
        node = ChangeGraph([{
            '@id': '_:1234',
            '@type': 'person',
            'given_name': 'Doe',
            'family_name': 'Jane',
        }]).nodes[0]

        assert node.id == '_:1234'
        assert node.type == 'person'
        assert node.is_blank is True
        assert node.attrs == {'given_name': 'Doe', 'family_name': 'Jane'}

    def test_is_blank(self):
        node = ChangeGraph([{
            '@id': '_:1234',
            '@type': 'person',
        }]).nodes[0]

        node._id = '1234'
        assert node.is_blank is False

    def test_extras(self):
        node = ChangeGraph([{
            '@id': '_:1234',
            '@type': 'person',
            'given_name': 'Doe',
            'family_name': 'Jane',
            'extra': {'likes': ['cats']}
        }]).nodes[0]

        assert 'extra' not in node.attrs
        assert node.extra == {'likes': ['cats']}

    # def test_mergeaction(self):
    #     node = ChangeNode.from_jsonld({
    #         '@id': '_:1234',
    #         '@type': 'MergeAction',
    #         'into': {'@type': 'Person', '@id': '1234'},
    #         'from': [
    #             {'@type': 'Person', '@id': '5827'},
    #             {'@type': 'Person', '@id': '0847'}
    #         ]
    #     })

    #     assert node.relations == {'into': {'@type': 'Person', '@id': '1234'}}
    #     assert node._reverse_relations == {
    #         'from': (
    #             {'@type': 'Person', '@id': '5827'},
    #             {'@type': 'Person', '@id': '0847'}
    #         )
    #     }

    def test_peels_context(self):
        node = ChangeGraph([{
            '@id': '_:5678',
            '@type': 'contributor',
            '@context': {'schema': 'www.example.com'},
        }]).nodes[0]

        assert node.context == {'schema': 'www.example.com'}

    def test_relationships(self):
        node = ChangeGraph([{
            '@id': '_:5678',
            '@type': 'contributor',
            'agent': {
                '@id': '_:1234',
                '@type': 'person'
            }
        }, {
            '@id': '_:1234',
            '@type': 'person'
        }]).nodes[1]

        assert node.type == 'contributor'
        assert node.attrs == {}
        assert len(node.related()) == 1
        assert node.related('agent').related.id == '_:1234'
        assert node.related('agent').related.type == 'person'


class TestChangeGraph:

    def test_single_node(self):
        graph = ChangeGraph([{
            '@id': '_:1234',
            '@type': 'person',
            'given_name': 'Doe',
            'family_name': 'Jane',
        }])

        assert len(graph.nodes) == 1

    def test_topological_sort(self):
        graph = ChangeGraph([{
            '@id': '_:5678',
            '@type': 'contributor',
            'agent': {
                '@id': '_:1234',
                '@type': 'person'
            }
        }, {
            '@id': '_:1234',
            '@type': 'person',
            'given_name': 'Doe',
            'family_name': 'Jane',
        }])

        assert len(graph.nodes) == 2
        assert graph.nodes[0].id == '_:1234'
        assert graph.nodes[1].id == '_:5678'
        assert len(graph.nodes[1].related()) == 1

    def test_topological_sort_many_to_many(self):
        graph = ChangeGraph([{
            '@id': '_:91011',
            '@type': 'preprint',
            'contributors': [{'@id': '_:5678', '@type': 'contributor'}]
        }, {
            '@id': '_:5678',
            '@type': 'contributor',
            'agent': {
                '@id': '_:1234',
                '@type': 'person'
            },
            'creative_work': {
                '@id': '_:91011',
                '@type': 'preprint'
            },
        }, {
            '@id': '_:1234',
            '@type': 'person',
            'given_name': 'Doe',
            'family_name': 'Jane',
        }])

        assert len(graph.nodes) == 3
        # assert graph.nodes[0].id == '_:1234'
        # assert graph.nodes[1].id == '_:91011'
        assert graph.nodes[2].id == '_:5678'

    def test_topological_sort_many_to_one(self):
        graph = ChangeGraph([{
            '@id': '_:91011',
            '@type': 'preprint',
            'identifiers': [{'@id': '_:5678', '@type': 'workidentifier'}]
        }, {
            '@id': '_:5678',
            '@type': 'workidentifier',
            'uri': 'mailto:gandhi@dinosaurs.sexy',
            'creative_work': {'@id': '_:91011', '@type': 'preprint'}
        }])

        assert len(graph.nodes) == 2
        assert graph.nodes[0].id == '_:91011'
        assert graph.nodes[1].id == '_:5678'

    def test_topological_sort_unchanged(self):
        graph = ChangeGraph([{
            '@id': '_:1234',
            '@type': 'person',
            'given_name': 'Doe',
            'family_name': 'Jane',
        }, {
            '@id': '_:5678',
            '@type': 'contributor',
            'person': {
                '@id': '_:1234',
                '@type': 'person'
            }
        }])

        assert len(graph.nodes) == 2
        assert graph.nodes[0].id == '_:1234'
        assert graph.nodes[1].id == '_:5678'

    def test_detect_cyclic(self):
        with pytest.raises(CyclicalDependency):
            ChangeGraph([{
                '@id': '_:1234',
                '@type': 'person',
                'given_name': 'Doe',
                'family_name': 'Jane',
                'contributor': {
                    '@id': '_:5678',
                    '@type': 'contributor',
                }
            }, {
                '@id': '_:5678',
                '@type': 'contributor',
                'agent': {
                    '@id': '_:1234',
                    '@type': 'person'
                }
            }])

    def test_unresolved_reference(self):
        with pytest.raises(UnresolvableReference) as e:
            ChangeGraph([{
                '@id': '_:5678',
                '@type': 'contributor',
                'agent': {
                    '@id': '_:1234',
                    '@type': 'person'
                }
            }]).process()
        assert e.value.args == (('_:1234', 'person'),)

    # def test_external_reference(self):
    #     ChangeGraph.from_jsonld({
    #         '@graph': [{
    #             '@id': '_:5678',
    #             '@type': 'contributor',
    #             'person': {
    #                 '@id': '8',
    #                 '@type': 'person'
    #             }
    #         }]
    #     }, disambiguate=False)

    # def test_parse_merge(self):
    #     graph = ChangeGraph.from_jsonld({
    #         '@graph': [{
    #             '@id': '_:123',
    #             '@type': 'MergeAction',
    #             'into': {'@id': 1, '@type': 'person'},
    #             'from': [{'@id': 2, '@type': 'person'}]
    #         }]
    #     }, disambiguate=False)

    #     assert len(graph.nodes) == 1
    #     assert len(graph.nodes[0].related) == 2
    #     assert len(graph.nodes[0].relations) == 1
    #     assert len(graph.nodes[0]._reverse_relations) == 1
