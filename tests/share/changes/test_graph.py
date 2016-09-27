import pytest

from share.change import ChangeNode
from share.change import ChangeGraph
from share.change import CyclicalDependency
from share.change import UnresolvableReference


class TestChangeNode:

    def test_from_ld(self):
        node = ChangeNode.from_jsonld({
            '@id': '_:1234',
            '@type': 'person',
            'given_name': 'Doe',
            'family_name': 'Jane',
        }, disambiguate=False)

        assert node.id == '_:1234'
        assert node.type == 'person'
        assert node.is_blank is True
        assert node.attrs == {'given_name': 'Doe', 'family_name': 'Jane'}

    def test_is_blank(self):
        node = ChangeNode.from_jsonld({
            '@id': 1234,
            '@type': 'person',
        }, disambiguate=False)

        assert node.is_blank is False

    def test_extras(self):
        node = ChangeNode.from_jsonld({
            '@id': '_:1234',
            '@type': 'person',
            'given_name': 'Doe',
            'family_name': 'Jane',
            'extra': {'likes': ['cats']}
        }, disambiguate=False)

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
    #     }, disambiguate=False)

    #     assert node.relations == {'into': {'@type': 'Person', '@id': '1234'}}
    #     assert node._reverse_relations == {
    #         'from': (
    #             {'@type': 'Person', '@id': '5827'},
    #             {'@type': 'Person', '@id': '0847'}
    #         )
    #     }

    def test_peels_context(self):
        node = ChangeNode.from_jsonld({
            '@id': '_:5678',
            '@type': 'contributor',
            '@context': {'schema': 'www.example.com'},
        }, disambiguate=False)

        assert node.context == {'@context': {'schema': 'www.example.com'}}

    def test_relationships(self):
        node = ChangeNode.from_jsonld({
            '@id': '_:5678',
            '@type': 'contributor',
            'person': {
                '@id': '_:1234',
                '@type': 'person'
            }
        }, disambiguate=False)

        assert node.attrs == {}
        assert len(node.relations) == 1
        assert node.relations['person'] == {'@id': '_:1234', '@type': 'person'}


class TestChangeGraph:

    def test_single_node(self):
        graph = ChangeGraph.from_jsonld({
            '@graph': [{
                '@id': '_:1234',
                '@type': 'person',
                'given_name': 'Doe',
                'family_name': 'Jane',
            }]
        }, disambiguate=False)

        assert len(graph.nodes) == 1

    def test_topological_sort(self):
        graph = ChangeGraph.from_jsonld({
            '@graph': [{
                '@id': '_:5678',
                '@type': 'contributor',
                'person': {
                    '@id': '_:1234',
                    '@type': 'person'
                }
            }, {
                '@id': '_:1234',
                '@type': 'person',
                'given_name': 'Doe',
                'family_name': 'Jane',
            }]
        }, disambiguate=False)

        assert len(graph.nodes) == 2
        assert graph.nodes[0].id == '_:1234'
        assert graph.nodes[1].id == '_:5678'
        assert len(graph.nodes[1].relations) == 1

    def test_topological_sort_many_to_many(self):
        graph = ChangeGraph.from_jsonld({
            '@graph': [{
                '@id': '_:91011',
                '@type': 'preprint',
                'contributors': [{'@id': '_:5678', '@type': 'contributor'}]
            }, {
                '@id': '_:5678',
                '@type': 'contributor',
                'person': {
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
            }]
        }, disambiguate=False)

        assert len(graph.nodes) == 3
        assert graph.nodes[0].id == '_:1234'
        assert graph.nodes[1].id == '_:91011'
        assert graph.nodes[2].id == '_:5678'

    def test_topological_sort_unchanged(self):
        graph = ChangeGraph.from_jsonld({
            '@graph': [{
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
            }]
        }, disambiguate=False)

        assert len(graph.nodes) == 2
        assert graph.nodes[0].id == '_:1234'
        assert graph.nodes[1].id == '_:5678'

    def test_detect_cyclic(self):
        with pytest.raises(CyclicalDependency):
            ChangeGraph.from_jsonld({
                '@graph': [{
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
                    'person': {
                        '@id': '_:1234',
                        '@type': 'person'
                    }
                }]
            }, disambiguate=False)

    def test_unresolved_reference(self):
        with pytest.raises(UnresolvableReference):
            ChangeGraph.from_jsonld({
                '@graph': [{
                    '@id': '_:5678',
                    '@type': 'contributor',
                    'person': {
                        '@id': '_:1234',
                        '@type': 'person'
                    }
                }]
            }, disambiguate=False)

    def test_external_reference(self):
        ChangeGraph.from_jsonld({
            '@graph': [{
                '@id': '_:5678',
                '@type': 'contributor',
                'person': {
                    '@id': 8,
                    '@type': 'person'
                }
            }]
        }, disambiguate=False)

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
