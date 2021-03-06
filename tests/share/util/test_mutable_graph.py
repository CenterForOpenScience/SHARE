import pytest

from share.util.graph import MutableGraph, MutableGraphError


work_id = '_:6203fec461bb4b3fa956772acbd9c50d'
org_id = '_:d486fd737bea4fbe9566b7a2842651ef'
uni_id = '_:d486fd737beeffbe9566b7a2842651ef'
person_id = '_:f4cec0271c7d4085bac26dbb2b32a002'
creator_id = '_:a17f28109536459ca02d99bf777400ae'
identifier_id = '_:a27f2810e536459ca02d99bf707400be'


@pytest.fixture
def example_graph_nodes():
    return [
        {'@id': uni_id, '@type': 'Institution', 'name': 'University of Whales'},
        {'@id': org_id, '@type': 'Organization', 'name': 'Department of Physics'},

        {'@id': '_:org-uni', '@type': 'IsMemberOf', 'subject': {'@id': org_id, '@type': 'Organization'}, 'related': {'@id': uni_id, '@type': 'Institution'}},

        {'@id': '_:tag1', '@type': 'Tag', 'name': 'you\'re'},
        {'@id': '_:tag2', '@type': 'Tag', 'name': 'it'},
        {'@id': '_:ttag1', '@type': 'ThroughTags', 'tag': {'@id': '_:tag1', '@type': 'Tag'}, 'creative_work': {'@id': work_id, '@type': 'Article'}},
        {'@id': '_:ttag2', '@type': 'ThroughTags', 'tag': {'@id': '_:tag2', '@type': 'Tag'}, 'creative_work': {'@id': work_id, '@type': 'Article'}},

        {'@id': '_:c4f10e02785a4b4d878f48d08ffc7fce', 'related': {'@type': 'Organization', '@id': org_id}, '@type': 'IsAffiliatedWith', 'subject': {'@type': 'Person', '@id': '_:7e742fa3377e4f119e36f8629144a0bc'}},
        {'@id': '_:7e742fa3377e4f119e36f8629144a0bc', 'agent_relations': [{'@type': 'IsAffiliatedWith', '@id': '_:c4f10e02785a4b4d878f48d08ffc7fce'}], '@type': 'Person', 'family_name': 'Prendergast', 'given_name': 'David'},
        {'@id': '_:687a4ba2cbd54ab7a2f2c3cd1777ea8a', '@type': 'Creator', 'creative_work': {'@type': 'Article', '@id': work_id}, 'agent': {'@type': 'Person', '@id': '_:7e742fa3377e4f119e36f8629144a0bc'}},

        {'@id': '_:69e859cefed140bd9b717c5b610d300c', '@type': 'Organization', 'name': 'NMRC, University College, Cork, Ireland'},

        {'@id': '_:2fd829eeda214adca2d4d34d02b10328', 'related': {'@type': 'Organization', '@id': '_:69e859cefed140bd9b717c5b610d300c'}, '@type': 'IsAffiliatedWith', 'subject': {'@type': 'Person', '@id': '_:ed3cc2a50f6d499db933a28d16bca5d6'}},
        {'@id': '_:ed3cc2a50f6d499db933a28d16bca5d6', 'agent_relations': [{'@type': 'IsAffiliatedWith', '@id': '_:2fd829eeda214adca2d4d34d02b10328'}], '@type': 'Person', 'family_name': 'Nolan', 'given_name': 'M.'},
        {'@id': '_:27961f3c7c644101a500772477aff304', '@type': 'Creator', 'creative_work': {'@type': 'Article', '@id': work_id}, 'agent': {'@type': 'Person', '@id': '_:ed3cc2a50f6d499db933a28d16bca5d6'}},

        {'@id': '_:d4f10e02785a4b4d878f48d08ffc7fce', 'related': {'@type': 'Organization', '@id': org_id}, '@type': 'IsAffiliatedWith', 'subject': {'@type': 'Person', '@id': '_:9a1386475d314b9bb524931e24361aaa'}},
        {'@id': '_:9a1386475d314b9bb524931e24361aaa', 'agent_relations': [{'@type': 'IsAffiliatedWith', '@id': '_:d4f10e02785a4b4d878f48d08ffc7fce'}], '@type': 'Person', 'family_name': 'Filippi', 'given_name': 'Claudia'},
        {'@id': '_:bf7726af4542405888463c796e5b7686', '@type': 'Creator', 'creative_work': {'@type': 'Article', '@id': work_id}, 'agent': {'@type': 'Person', '@id': '_:9a1386475d314b9bb524931e24361aaa'}},

        {'@id': '_:e4f10e02785a4b4d878f48d08ffc7fce', 'related': {'@type': 'Organization', '@id': org_id}, '@type': 'IsAffiliatedWith', 'subject': {'@type': 'Person', '@id': '_:78639db07e2e4ee88b422a8920d8a095'}},
        {'@id': '_:78639db07e2e4ee88b422a8920d8a095', 'agent_relations': [{'@type': 'IsAffiliatedWith', '@id': '_:e4f10e02785a4b4d878f48d08ffc7fce'}], '@type': 'Person', 'family_name': 'Fahy', 'given_name': 'Stephen'},
        {'@id': '_:18d151204d7c431388a7e516defab1bc', '@type': 'Creator', 'creative_work': {'@type': 'Article', '@id': work_id}, 'agent': {'@type': 'Person', '@id': '_:78639db07e2e4ee88b422a8920d8a095'}},

        {'@id': '_:5fd829eeda214adca2d4d34d02b10328', 'related': {'@type': 'Organization', '@id': '_:69e859cefed140bd9b717c5b610d300c'}, '@type': 'IsAffiliatedWith', 'subject': {'@type': 'Person', '@id': person_id}},
        {'@id': person_id, 'agent_relations': [{'@type': 'IsAffiliatedWith', '@id': '_:5fd829eeda214adca2d4d34d02b10328'}], '@type': 'Person', 'family_name': 'Greer', 'given_name': 'J.'},
        {'@id': creator_id, '@type': 'Creator', 'creative_work': {'@type': 'Article', '@id': work_id}, 'agent': {'@type': 'Person', '@id': person_id}},
        {'@id': identifier_id, '@type': 'WorkIdentifier', 'creative_work': {'@type': 'Article', '@id': work_id}, 'uri': 'http://example.com/things'},
        {'@id': work_id, 'date_updated': '2016-10-20T00:00:00+00:00', 'identifiers': [{'@type': 'WorkIdentifier', '@id': identifier_id}], 'agent_relations': [{'@type': 'Creator', '@id': '_:687a4ba2cbd54ab7a2f2c3cd1777ea8a'}, {'@type': 'Creator', '@id': '_:27961f3c7c644101a500772477aff304'}, {'@type': 'Creator', '@id': '_:bf7726af4542405888463c796e5b7686'}, {'@type': 'Creator', '@id': '_:18d151204d7c431388a7e516defab1bc'}, {'@type': 'Creator', '@id': creator_id}], 'title': 'Impact of Electron-Electron Cusp on Configuration Interaction Energies', '@type': 'Article', 'description': '  The effect of the electron-electron cusp on the convergence of configuration\ninteraction (CI) wave functions is examined. By analogy with the\npseudopotential approach for electron-ion interactions, an effective\nelectron-electron interaction is developed which closely reproduces the\nscattering of the Coulomb interaction but is smooth and finite at zero\nelectron-electron separation. The exact many-electron wave function for this\nsmooth effective interaction has no cusp at zero electron-electron separation.\nWe perform CI and quantum Monte Carlo calculations for He and Be atoms, both\nwith the Coulomb electron-electron interaction and with the smooth effective\nelectron-electron interaction. We find that convergence of the CI expansion of\nthe wave function for the smooth electron-electron interaction is not\nsignificantly improved compared with that for the divergent Coulomb interaction\nfor energy differences on the order of 1 mHartree. This shows that, contrary to\npopular belief, description of the electron-electron cusp is not a limiting\nfactor, to within chemical accuracy, for CI calculations.\n'}  # noqa
    ]


@pytest.fixture
def example_graph(example_graph_nodes):
    return MutableGraph.from_jsonld(example_graph_nodes)


class TestMutableGraph:
    def test_graph(self, example_graph):
        assert example_graph.number_of_nodes() == 25

    @pytest.mark.parametrize('node_id', [work_id, org_id, person_id, creator_id])
    def test_get_node(self, example_graph, node_id):
        assert example_graph.get_node(node_id).id == node_id

    def test_get_nonexistent_node(self, example_graph):
        assert example_graph.get_node('not_an_id') is None

    def test_edge(self, example_graph):
        creator_node = example_graph.get_node(creator_id)
        assert creator_node['creative_work'] == example_graph.get_node(work_id)
        assert creator_node['agent'] == example_graph.get_node(person_id)

    @pytest.mark.parametrize('node_id, key, value', [
        (work_id, 'title', 'title title'),
        (work_id, 'description', 'woo'),
        (identifier_id, 'creative_work', None),
        (identifier_id, 'foo', 'bar'),
    ])
    def test_set_attrs(self, example_graph, node_id, key, value):
        n = example_graph.get_node(node_id)
        n[key] = value
        assert n[key] == value

    @pytest.mark.parametrize('set_none', [True, False])
    def test_del_attrs(self, example_graph, set_none):
        work = example_graph.get_node(work_id)
        assert work['title']
        if set_none:
            work['title'] = None
        else:
            del work['title']
        assert work['title'] is None
        assert 'title' not in work.attrs()

        identifier = example_graph.get_node(identifier_id)
        assert identifier['creative_work'] == work
        if set_none:
            identifier['creative_work'] = None
        else:
            del identifier['creative_work']

    @pytest.mark.parametrize('node_id, reverse_edge_name, count', [
        (work_id, 'agent_relations', 5),
        (work_id, 'incoming_creative_work_relations', 0),
        (work_id, 'identifiers', 1),
        (org_id, 'incoming_agent_relations', 3),
        (org_id, 'outgoing_agent_relations', 1),
    ])
    def test_reverse_edge(self, example_graph, node_id, reverse_edge_name, count):
        node = example_graph.get_node(node_id)
        assert len(node[reverse_edge_name]) == count

    @pytest.mark.parametrize('node_id, m2m_name, count', [
        (work_id, 'related_agents', 5),
        (work_id, 'related_works', 0),
        (work_id, 'subjects', 0),
        (work_id, 'tags', 2),
        (org_id, 'related_works', 0),
        (org_id, 'related_agents', 4),
    ])
    def test_many_to_many(self, example_graph, node_id, m2m_name, count):
        node = example_graph.get_node(node_id)
        assert len(node[m2m_name]) == count

    @pytest.mark.parametrize('node_id, count', [
        (work_id, 16),
        (org_id, 20),
        (person_id, 22),
        (creator_id, 24),
    ])
    def test_remove_node_cascades(self, example_graph, node_id, count):
        example_graph.remove_node(node_id)
        assert example_graph.number_of_nodes() == count

    def test_add_node(self, example_graph):
        identifier_id = '_:foo'
        uri = 'mailto:person@example.com'
        person = example_graph.get_node(person_id)
        node_count = example_graph.number_of_nodes()
        assert len(person['identifiers']) == 0

        example_graph.add_node(identifier_id, 'AgentIdentifier', {'uri': uri, 'agent': person})

        assert example_graph.number_of_nodes() == node_count + 1
        identifier_node = example_graph.get_node(identifier_id)
        assert identifier_node['uri'] == uri
        assert identifier_node['agent'] == person

        identifiers = person['identifiers']
        assert len(identifiers) == 1
        assert identifier_node == next(iter(identifiers))

    @pytest.mark.parametrize('count, filter', [
        (5, lambda n, g: n.type == 'person'),
        (0, lambda n, g: not g.degree(n.id)),
        (1, lambda n, g: len(g.out_edges(n.id)) == 1),
    ])
    def test_filter_nodes(self, example_graph, filter, count):
        filtered = list(example_graph.filter_nodes(lambda n: filter(n, example_graph)))
        assert len(filtered) == count

    def test_jsonld(self, example_graph_nodes, example_graph):
        def clean_jsonld(value):
            if isinstance(value, list):
                return [clean_jsonld(n) for n in sorted(value, key=lambda n: n['@id'])]
            if isinstance(value, dict):
                return {
                    k: v.lower() if k == '@type' else clean_jsonld(v)
                    for k, v in value.items() if not isinstance(v, list)
                }
            return value
        expected_nodes = clean_jsonld(example_graph_nodes)
        actual = example_graph.to_jsonld(in_edges=False)
        actual_nodes = clean_jsonld(actual['@graph'])
        assert expected_nodes == actual_nodes
        assert actual['central_node_id'] is None


class TestCentralWork:
    def test_obvious_example(self, example_graph):
        assert example_graph.central_node_id is None
        assert example_graph.get_central_node() is None

        guessed = example_graph.get_central_node(guess=True)
        assert guessed.id == work_id
        # side-effect: now the graph knows its central node
        assert example_graph.central_node_id == work_id
        assert example_graph.get_central_node() == guessed

    def test_no_central_node(self):
        graph = MutableGraph()
        agent = graph.add_node(None, 'agent')
        graph.add_node(None, 'agentidentifier', {'agent': agent})

        assert graph.get_central_node() is None
        assert graph.get_central_node(guess=True) is None
        assert graph.central_node_id is None

    def test_explicit_central_node(self):
        central_id = '_:center'

        graph = MutableGraph.from_jsonld({
            'central_node_id': central_id,
            '@graph': [
                {'@id': central_id, '@type': 'creativework'},
                {'@id': '_:other', '@type': 'creativework', 'title': 'looks like the center'},
            ],
        })
        assert graph.central_node_id == central_id
        assert graph.get_central_node().id == central_id
        assert graph.get_central_node(guess=True).id == central_id

    def test_ambiguous_central_node(self):
        graph = MutableGraph.from_jsonld({
            '@graph': [
                {'@id': '_:thing1', '@type': 'creativework', 'title': 'looks like the center'},
                {'@id': '_:thing2', '@type': 'creativework', 'title': 'also looks like the center'},
            ],
        })
        with pytest.raises(MutableGraphError):
            graph.get_central_node(guess=True)

    @pytest.mark.parametrize('graph_nodes, expected_guess', [
        (
            [
                {'@id': '_:thing1', '@type': 'creativework', 'title': 'only thing'},
            ],
            '_:thing1',
        ),
        (
            [
                {'@id': '_:thing1', '@type': 'creativework', 'title': 'one thing'},
                {'@id': '_:thing2', '@type': 'creativework', 'title': 'another thing', 'description': 'tiebreaker'},
            ],
            '_:thing2',
        ),
        (
            [
                {'@id': '_:thing1', '@type': 'creativework', 'title': 'looks like the center'},
                {'@id': '_:thing2', '@type': 'creativework', 'title': 'also looks like the center'},
                {
                    '@id': '_:tiebreaker',
                    '@type': 'workidentifier',
                    'uri': 'http://example.com/woo',
                    'creative_work': {'@id': '_:thing2', '@type': 'creativework'},
                },
            ],
            '_:thing2',
        ),
        (
            [
                {'@id': '_:thing1', '@type': 'creativework', 'title': 'looks like the center', 'description': 'confounder'},
                {'@id': '_:thing2', '@type': 'creativework', 'title': 'also looks like the center'},
                {
                    '@id': '_:tiebreaker',
                    '@type': 'workidentifier',
                    'uri': 'http://example.com/woo',
                    'creative_work': {'@id': '_:thing2', '@type': 'creativework'},
                },
            ],
            '_:thing2',
        ),
        (
            [
                {'@id': '_:thing1', '@type': 'creativework', 'title': 'parent'},
                {'@id': '_:thing2', '@type': 'creativework', 'title': 'child'},
                {
                    '@id': '_:choose-the-child',
                    '@type': 'ispartof',
                    'subject': {'@id': '_:thing2', '@type': 'creativework'},
                    'related': {'@id': '_:thing1', '@type': 'creativework'},
                },
            ],
            '_:thing2',
        ),
    ])
    def test_guessing(self, graph_nodes, expected_guess):
        graph = MutableGraph.from_jsonld({'@graph': graph_nodes})
        guessed = graph.get_central_node(guess=True)
        assert guessed.id == expected_guess
