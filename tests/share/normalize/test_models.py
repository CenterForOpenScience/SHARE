import pytest

from share.utils.graph import MutableGraph
from share.regulate import Regulator

from tests.share.normalize.factories import Tag, CreativeWork, Person, Agent, \
    Institution, Organization, AgentIdentifier, Creator, Contributor, Funder, Publisher, Host


class TestModelNormalization:

    # test each tag resolves to lowercased, tokenized name
    @pytest.mark.parametrize('input, output', [(i, o) for input, o in [
        ([
            Tag(name=''),
            Tag(name='        '),
            Tag(name='\n\n\n'),
        ], []),
        ([
            Tag(name='foo'),
            Tag(name='foO'),
            Tag(name='Foo'),
            Tag(name='FOO'),
            Tag(name='      FOO'),
            Tag(name='      foo\n\n\n'),
        ], [Tag(name='foo')]),
        ([
            Tag(name='Rocket League'),
            Tag(name='rocket league'),
            Tag(name='ROCKET LEAGUE'),
            Tag(name='Rocket         League'),
            Tag(name='\nRocket    \n     League\t'),
            Tag(name='rocket\nleague'),
        ], [Tag(name='rocket league')]),
        ([
            Tag(name='Crash; Bandicoot'),
            Tag(name='Crash;           Bandicoot'),
            Tag(name='\nCrash; Bandicoot'),
            Tag(name='crash, bandicoot'),
            Tag(name='Crash ,Bandicoot           '),
        ], [Tag(name='bandicoot'), Tag(name='crash')]),
    ] for i in input])
    def test_normalize_tag(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(CreativeWork(tags=[input])))
        Regulator().regulate(graph)

        assert graph.to_jsonld(in_edges=False) == JsonLD(CreativeWork(tags=output))

    # test tags with the same name are merged on a work
    @pytest.mark.parametrize('input, output', [
        ([
            Tag(name=''),
            Tag(name='        '),
            Tag(name='\n\n\n'),
        ], []),
        ([
            Tag(name='foo'),
            Tag(name='foO'),
            Tag(name='Foo'),
            Tag(name='FOO'),
            Tag(name='      FOO'),
            Tag(name='      foo\n\n\n'),
        ], [Tag(name='foo')]),
        ([
            Tag(name='Rocket League'),
            Tag(name='rocket league'),
            Tag(name='ROCKET LEAGUE'),
            Tag(name='Rocket         League'),
            Tag(name='\nRocket    \n     League\t'),
            Tag(name='rocket\nleague'),
        ], [Tag(name='rocket league')]),
        ([
            Tag(name='Crash; Bandicoot'),
            Tag(name='Crash;           Bandicoot'),
            Tag(name='\nCrash; Bandicoot'),
            Tag(name='crash, bandicoot'),
            Tag(name='Crash ,Bandicoot           '),
        ], [Tag(name='bandicoot'), Tag(name='crash')]),
    ])
    def test_normalize_tags_on_work(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(CreativeWork(tags=input)))
        Regulator().regulate(graph)
        assert graph.to_jsonld(in_edges=False) == JsonLD(CreativeWork(tags=output))

    @pytest.mark.parametrize('input, output', [(i, o) for input, o in [
        ([
            Person(name='Smith, J'),
            Person(name='J    Smith   '),
            Person(name='Smith,     J'),
            Person(given_name='J', family_name='Smith'),
            Person(given_name='  J', family_name='\n\nSmith'),
        ], Person(name='J Smith', family_name='Smith', given_name='J')),
        ([
            Person(name='Johnathan James Doe'),
            Person(name='johnathan james doe'),
        ], Person(name='Johnathan James Doe', family_name='Doe', given_name='Johnathan', additional_name='James')),
        ([
            Person(name='johnathan james doe JR'),
        ], Person(name='Johnathan James Doe Jr', family_name='Doe', given_name='Johnathan', additional_name='James', suffix='Jr')),
        ([
            Person(name='none'),
            Person(name=''),
            Person(name='NULL'),
            Person(name='None'),
            Person(name='           '),
            Person(name='     None      '),
        ], None)
    ] for i in input])
    def test_normalize_person(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(input))
        Regulator().regulate(graph)
        assert graph.to_jsonld(in_edges=False) == (JsonLD(output) if output else [])

    # test two people with the same identifier are merged
    # sort by length and then alphabetize name field
    @pytest.mark.parametrize('input, output', [
        # same name, same identifier
        ([
            Person(0, name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(1, name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(2, name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
        ], [Person(2, name='Barb Dylan', parse=True, identifiers=[AgentIdentifier(1)])]),
        ([
            Person(0, name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(1, name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(2, name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(3, name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
        ], [Person(3, name='Barb Dylan', parse=True, identifiers=[AgentIdentifier(1)])]),
        # same name, different identifiers
        ([
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(2)])
        ], [
            Person(name='Barb Dylan', parse=True, identifiers=[AgentIdentifier(1)]),
            Person(name='Barb Dylan', parse=True, identifiers=[AgentIdentifier(2)])
        ]),
        # no name - name, same identifier
        ([
            Person(name='', identifiers=[AgentIdentifier(1)]),
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)])
        ], [Person(name='Barb Dylan', parse=True, identifiers=[AgentIdentifier(1)])]),
        # two names, same identifier, take longer name
        ([
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='Barbra Dylan', identifiers=[AgentIdentifier(1)])
        ], [Person(name='Barbra Dylan', parse=True, identifiers=[AgentIdentifier(1)])]),
        # two sames, same length, same identifier, alphabetize and take first
        ([
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='Aarb Dylan', identifiers=[AgentIdentifier(1)])
        ], [Person(name='Aarb Dylan', parse=True, identifiers=[AgentIdentifier(1)])]),
        # 3 different names, take longest of each name field
        ([
            # Below case WILL FAIL. Haven't seen just a last name... yet
            # Person(name='Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='Dylan, B', identifiers=[AgentIdentifier(1)]),
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='B. D. Dylan', identifiers=[AgentIdentifier(1)])
        ], [Person(name='Barb D. Dylan', parse=True, identifiers=[AgentIdentifier(1)])]),
    ])
    def test_normalize_person_relation(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(*input))
        Regulator().regulate(graph)
        assert graph.to_jsonld(in_edges=False) == JsonLD(*output)

    @pytest.mark.parametrize('input, output', [
        (Agent(name='none'), None),
        (Agent(name=''), None),
        (Agent(name='NULL'), None),
        (Agent(name='None'), None),
        (Agent(name='           '), None),
        (Agent(name='     None      '), None),
        (Agent(name='     Empty Foundation      '), Organization(name='Empty Foundation')),
        (Agent(name='University \n of Arizona '), Institution(name='University of Arizona')),
        (Agent(name='NMRC, University College, Cork, Ireland'), Institution(name='NMRC, University College', location='Cork, Ireland')),
        (Agent(name='Ioffe Physico-Technical Institute'), Institution(name='Ioffe Physico-Technical Institute')),
        (Agent(name='DPTA'), Organization(name='DPTA')),
        (Agent(name='B. Verkin Institute for Low Temperatures Physics & Engineering, Kharkov, Ukraine'), Institution(name='B. Verkin Institute for Low Temperatures Physics & Engineering', location='Kharkov, Ukraine', type='institution')),
        (Agent(name='Physikalisches Institut, University Wuerzburg, Germany'), Agent(name='Physikalisches Institut', location='University Wuerzburg, Germany', type='institution')),
        (Agent(name='Centro de Biotecnologia e Departamento de Biofísica; UFRGS; Av Bento Goncalves 9500, Predio 43431 sala 213 91501-970 Porto Alegre Rio Grande do Sul Brazi'), Agent(name='UFRGS - Centro de Biotecnologia e Departamento de Biofísica', location='Av Bento Goncalves 9500, Predio 43431 Sala 213 91501-970 Porto Alegre Rio Grande do Sul Brazi')),
        (Agent(name='Department of Chemistry; ZheJiang University; HangZhou ZheJiang CHINA'), Institution(name='ZheJiang University - Department of Chemistry', location='HangZhou ZheJiang CHINA')),
        (Agent(name='Marine Evolution and Conservation; Groningen Institute for Evolutionary Life Sciences; University of Groningen; Nijenborgh 7, 9747 AG Groningen The Netherlands'), Institution(name='University of Groningen - Marine Evolution and Conservation; Groningen Institute for Evolutionary Life Sciences', location='Nijenborgh 7, 9747 AG Groningen The Netherlands')),
        (Agent(name='Institute of Marine Research; PO Box 1870 Nordnes, 5817 Bergen Norway'), Institution(name='Institute of Marine Research', location='PO Box 1870 Nordnes, 5817 Bergen Norway')),
        (Agent(name='    PeerJ    Inc.    '), Organization(name='PeerJ Inc.')),
        (Agent(name=' Clinton   Foundation\n   '), Organization(name='Clinton Foundation')),
    ])
    def test_normalize_agent(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(input))
        Regulator().regulate(graph)
        assert graph.to_jsonld(in_edges=False) == (JsonLD(output) if output else [])

    # test two organizations/institutions with the same name are merged
    # sort by length and then alphabetize name field
    @pytest.mark.parametrize('input, output', [
        # same name, same identifiers
        ([
            Organization(name='American Heart Association', identifiers=[AgentIdentifier(1)]),
            Organization(name='American Heart Association', identifiers=[AgentIdentifier(1)])
        ], [Organization(name='American Heart Association', identifiers=[AgentIdentifier(1)])]),
        # same name, different identifiers
        ([
            Organization(name='Money Foundation', identifiers=[AgentIdentifier(1)]),
            Organization(name='Money Foundation', identifiers=[AgentIdentifier(2)])
        ], [
            Organization(name='Money Foundation', identifiers=[AgentIdentifier(1), AgentIdentifier(2)])
        ]),
        # same name, different identifiers, different capitilization
        ([
            Organization(name='Money Foundation', identifiers=[AgentIdentifier(1)]),
            Organization(name='MONEY FOUNDATION', identifiers=[AgentIdentifier(2)])
        ], [
            Organization(name='Money Foundation', identifiers=[AgentIdentifier(1)]),
            Organization(name='MONEY FOUNDATION', identifiers=[AgentIdentifier(2)])
        ]),
        # same identifier, different type, accept more specific type
        ([
            Institution(name='University of Virginia', identifiers=[AgentIdentifier(1)]),
            Organization(name='University of Virginia', identifiers=[AgentIdentifier(1)]),
        ], [
            Institution(name='University of Virginia', identifiers=[AgentIdentifier(1)])
        ]),
        # same identifier, same name, same length, different capitilization, alphabetize
        ([
            Organization(name='Share', identifiers=[AgentIdentifier(1)]),
            Organization(name='SHARE', identifiers=[AgentIdentifier(1)])
        ], [Organization(name='SHARE', identifiers=[AgentIdentifier(1)])]),
        # same name, one identifier, add identifier
        ([
            Organization(name='Timetables Inc.'),
            Organization(name='Timetables Inc.', identifiers=[AgentIdentifier(1)])
        ], [Organization(name='Timetables Inc.', identifiers=[AgentIdentifier(1)])]),
        # same identifier, different name, accept longest alphabetize
        ([
            Institution(name='Cooking Institute', identifiers=[AgentIdentifier(1)]),
            Institution(name='Cooking Instituze', identifiers=[AgentIdentifier(1)]),
            Institution(name='Cook Institute', identifiers=[AgentIdentifier(1)])
        ], [Institution(name='Cooking Institute', identifiers=[AgentIdentifier(1)])]),
    ])
    def test_normalize_organization_institution_name(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(*input))
        Regulator().regulate(graph)
        assert graph.to_jsonld(in_edges=False) == JsonLD(*output)

    # test different types of agent work relations
    # Funder, Publisher, Host
    @pytest.mark.parametrize('input, output', [
        # same name, same identifiers
        ([
            Funder(cited_as='American Heart Association', agent=Organization(1, id=1, name='American Heart Association', identifiers=[AgentIdentifier(1, id=0)])),
            Host(cited_as='American Heart Association', agent=Organization(2, id=1, name='American Heart Association', identifiers=[AgentIdentifier(1)]))
        ], [
            Funder(cited_as='American Heart Association', agent=Organization(1, id=1, name='American Heart Association', identifiers=[AgentIdentifier(1, id=0)])),
            Host(cited_as='American Heart Association', agent=Organization(1, id=1, name='American Heart Association', identifiers=[AgentIdentifier(1, id=0)]))
        ]),
        # same name, different identifiers
        ([
            Funder(cited_as='Money Foundation', agent=Organization(id=1, name='Money Foundation', identifiers=[AgentIdentifier(1)])),
            Host(cited_as='Money Foundation', agent=Organization(name='Money Foundation', identifiers=[AgentIdentifier(2)]))
        ], [
            Funder(cited_as='Money Foundation', agent=Organization(id=1, name='Money Foundation', identifiers=[AgentIdentifier(1), AgentIdentifier(2)])),
            Host(cited_as='Money Foundation', agent=Organization(id=1, name='Money Foundation'))
        ]),
        # same identifier, different type
        ([
            Funder(cited_as='University of Virginia', agent=Institution(id=1, name='University of Virginia', identifiers=[AgentIdentifier(1)])),
            Publisher(cited_as='University of Virginia', agent=Institution(name='University of Virginia', identifiers=[AgentIdentifier(1, id=0)]))
        ], [
            Funder(cited_as='University of Virginia', agent=Institution(id=1, name='University of Virginia', identifiers=[AgentIdentifier(1, id=0)])),
            Publisher(cited_as='University of Virginia', agent=Institution(id=1, name='University of Virginia'))
        ]),
        # same identifier, same name, same length, different capitilization, alphabetize
        ([
            Publisher(cited_as='Share', agent=Organization(id=0, name='Share', identifiers=[AgentIdentifier(1, id=2)])),
            Host(cited_as='SHARE', agent=Organization(id=1, name='SHARE', identifiers=[AgentIdentifier(1, id=3)]))
        ], [
            Publisher(cited_as='Share', agent=Organization(id=1, name='SHARE', identifiers=[AgentIdentifier(1, id=3)])),
            Host(cited_as='SHARE', agent=Organization(id=1, name='SHARE'))
        ]),
        # same name, one identifier, add identifier
        ([
            Funder(cited_as='Timetables Inc.', agent=Organization(id=1, name='Timetables Inc.')),
            Publisher(cited_as='Timetables Inc.', agent=Organization(id=2, name='Timetables Inc.', identifiers=[AgentIdentifier(1)]))
        ], [
            Funder(cited_as='Timetables Inc.', agent=Organization(id=2, name='Timetables Inc.', identifiers=[AgentIdentifier(1)])),
            Publisher(cited_as='Timetables Inc.', agent=Organization(id=2))
        ]),
        # same identifier, different name, accept longest alphabetize
        ([
            Funder(cited_as='Cooking Institute', agent=Organization(id=1, name='Cooking Notaninstitute', identifiers=[AgentIdentifier(1)])),
            Publisher(cited_as='Cooking Instituze', agent=Organization(id=2, name='Cooking Notaninstituze', identifiers=[AgentIdentifier(1)])),
            Host(cited_as='Cook Institute', agent=Organization(id=3, name='Cook Notaninstitute', identifiers=[AgentIdentifier(1)]))
        ], [
            Funder(cited_as='Cooking Institute', agent=Organization(id=3, name='Cooking Notaninstitute', identifiers=[AgentIdentifier(1)])),
            Publisher(cited_as='Cooking Instituze', agent=Organization(id=3)),
            Host(cited_as='Cook Institute', agent=Organization(id=3))
        ]),
        # same identifier, different name, different type, accept longest alphabetize, more specific
        ([
            Funder(cited_as='Cooking Institute', agent=Institution(id=1, name='Cooking Notaninstitute', identifiers=[AgentIdentifier(1)])),
            Publisher(cited_as='Cooking Instituze', agent=Organization(id=2, name='Cooking Notaninstituze', identifiers=[AgentIdentifier(1)])),
            Host(cited_as='Cook Institute', agent=Institution(id=3, name='Cook Notaninstitute', identifiers=[AgentIdentifier(1)]))
        ], [
            Funder(cited_as='Cooking Institute', agent=Institution(id=3, name='Cooking Notaninstitute', identifiers=[AgentIdentifier(1)])),
            Publisher(cited_as='Cooking Instituze', agent=Institution(id=3)),
            Host(cited_as='Cook Institute', agent=Institution(id=3))
        ]),
    ])
    def test_normalize_mixed_agent_relation(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(CreativeWork(agent_relations=input)))
        Regulator().regulate(graph)
        assert graph.to_jsonld(in_edges=False) == JsonLD(CreativeWork(agent_relations=output))

    # test different types of agent work relations
    # Contributor, Creator
    @pytest.mark.parametrize('input, output', [
        # same name, same identifiers, different type, same type tree, organization
        ([
            Creator(cited_as='American Heart Association', agent=Organization(id=0, name='American Heart Association', identifiers=[AgentIdentifier(1, id=1)])),
            Contributor(cited_as='American Heart Association', agent=Organization(id=1, name='American Heart Association', identifiers=[AgentIdentifier(1, id=2)]))
        ], [
            Creator(cited_as='American Heart Association', agent=Organization(id=1, name='American Heart Association', identifiers=[AgentIdentifier(1, id=2)]))
        ]),
        # same name, different identifiers, different type, same type tree
        ([
            Creator(cited_as='Money Foundation', agent=Organization(id=1, name='Money Foundation', identifiers=[AgentIdentifier()])),
            Contributor(cited_as='Money Foundation', agent=Organization(id=2, name='Money Foundation', identifiers=[AgentIdentifier()])),
        ], [
            Creator(cited_as='Money Foundation', agent=Organization(id=2, name='Money Foundation', identifiers=[AgentIdentifier(), AgentIdentifier()]))
        ]),
        # same identifier, same name, different type
        ([
            Contributor(cited_as='University of Virginia', agent=Institution(id=0, name='University of Virginia', identifiers=[AgentIdentifier(1, id=1)])),
            Publisher(cited_as='University of Virginia', agent=Institution(id=1, name='University of Virginia', identifiers=[AgentIdentifier(1, id=1)]))
        ], [
            Contributor(cited_as='University of Virginia', agent=Institution(id=1, name='University of Virginia', identifiers=[AgentIdentifier(1, id=1)])),
            Publisher(cited_as='University of Virginia', agent=Institution(id=1, name='University of Virginia', identifiers=[AgentIdentifier(1, id=1)]))
        ]),
        # same identifier, same name, different type, same type tree, person
        ([
            Creator(cited_as='Bob Dylan', agent=Person(id=0, name='Bob Dylan', identifiers=[AgentIdentifier(1, id=0)])),
            Contributor(cited_as='Bob Dylan', agent=Person(id=1, name='Bob Dylan', identifiers=[AgentIdentifier(1, id=1)])),
        ], [
            Creator(cited_as='Bob Dylan', agent=Person(id=1, name='Bob Dylan', given_name='Bob', family_name='Dylan', identifiers=[AgentIdentifier(1, id=1)]))
        ]),
        # same identifier, different name, different type
        ([
            Creator(cited_as='B. Dylan', agent=Person(id=0, name='B. Dylan', identifiers=[AgentIdentifier(1, id=0)])),
            Contributor(cited_as='Bob Dylan', agent=Person(id=1, name='Bob Dylan', identifiers=[AgentIdentifier(1, id=1)])),
        ], [
            Creator(cited_as='Bob Dylan', agent=Person(id=1, name='Bob Dylan', given_name='Bob', family_name='Dylan', identifiers=[AgentIdentifier(1, id=1)]))
        ]),
        # same name, one identifier, add identifier
        ([
            Creator(1, id=0, order_cited=4, cited_as='Timetables Inc.', agent=Organization(id=0, name='Timetables Inc.')),
            Creator(1, id=1, order_cited=20, cited_as='Timetables Inc.', agent=Organization(id=1, name='Timetables Inc.', identifiers=[AgentIdentifier()]))
        ], [
            Creator(1, id=1, order_cited=20, cited_as='Timetables Inc.', agent=Organization(id=1, name='Timetables Inc.', identifiers=[AgentIdentifier()]))
        ]),
        # same identifier, different name, accept longest alphabetize
        ([
            Creator(cited_as='Cooking Institute', agent=Organization(id=1, name='Cooking Institute', identifiers=[AgentIdentifier(1, id=1)])),
            Contributor(cited_as='Cooking Instituze', agent=Organization(id=2, name='Cooking Instituze', identifiers=[AgentIdentifier(1, id=2)])),
            Funder(cited_as='Cook Institute', agent=Organization(id=3, name='Cook Institute', identifiers=[AgentIdentifier(1, id=3)]))
        ], [
            Creator(cited_as='Cooking Institute', agent=Institution(id=3, name='Cooking Institute', identifiers=[AgentIdentifier(1, id=3)])),
            Funder(cited_as='Cook Institute', agent=Institution(id=3, name='Cooking Institute', identifiers=[AgentIdentifier(1, id=3)]))
        ]),
        # same identifier, different name, different type, accept longest alphabetize, more specific
        ([
            Creator(cited_as='Cooking Institute', order_cited=10, agent=Institution(id=0, name='Cooking Institute', identifiers=[AgentIdentifier(1, id=1)])),
            Contributor(cited_as='Cooking Instituze', order_cited=3, agent=Organization(id=1, name='Cooking Instituze', identifiers=[AgentIdentifier(1, id=2)])),
            Funder(cited_as='Cook Institute', agent=Institution(id=2, name='Cook Institute', identifiers=[AgentIdentifier(1, id=3)]))
        ], [
            Creator(cited_as='Cooking Institute', order_cited=10, agent=Institution(id=2, name='Cooking Institute', identifiers=[AgentIdentifier(1, id=3)])),
            Funder(cited_as='Cook Institute', agent=Institution(id=2, name='Cooking Institute', identifiers=[AgentIdentifier(1, id=3)]))
        ]),
        # Related agent removed
        ([
            Creator(cited_as='', agent=Person(id=0, name='None', identifiers=[AgentIdentifier(1, id=1)])),
        ], [
        ])
    ])
    def test_normalize_contributor_creator_relation(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(CreativeWork(agent_relations=input)))
        Regulator().regulate(graph)
        assert graph.to_jsonld(in_edges=False) == JsonLD(CreativeWork(agent_relations=output))

    # test work with related work
    @pytest.mark.parametrize('input, output', [
        # different identifiers
        (CreativeWork(1, related_works=[CreativeWork(2)]), CreativeWork(1, related_works=[CreativeWork(2)])),
        # same identifiers
        (CreativeWork(1, id=1, related_works=[CreativeWork(1, id=1)]), CreativeWork(1, id=1)),
        # same and different identifiers
        (CreativeWork(1, id=1, related_works=[CreativeWork(2, id=2), CreativeWork(1, id=1)]), CreativeWork(1, id=1, related_works=[CreativeWork(2, id=2)]))
    ])
    def test_normalize_related_work(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(input))
        Regulator().regulate(graph)
        assert graph.to_jsonld(in_edges=False) == JsonLD(output)

    @pytest.mark.parametrize('input, output', [
        ({'title': '', 'description': ''}, {'title': '', 'description': ''}),
        ({'title': '    ', 'description': '     '}, {'title': '', 'description': ''}),
        ({'title': 'Title\nLine'}, {'title': 'Title Line'}),
        ({'description': 'Line\nAfter\nLine\nAfter\nLine'}, {'description': 'Line After Line After Line'}),
        ({'description': 'null'}, {'description': ''}),
    ])
    def test_normalize_creativework(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(CreativeWork(**input)))
        Regulator().regulate(graph)
        assert graph.to_jsonld(in_edges=False) == JsonLD(CreativeWork(**output))

    @pytest.mark.parametrize('input, output', [
        (input, Creator(cited_as='James Bond', agent=Person(name='James Bond', family_name='Bond', given_name='James')),)
        for input in [
            Creator(cited_as='   \t James\n Bond \t     ', agent=Person(name='James  Bond')),
            Creator(cited_as='', agent=Person(name='James  Bond')),
            Creator(cited_as='', agent=Person(name='James      Bond')),
            Creator(cited_as='', agent=Person(given_name='James', family_name='Bond')),
        ]
    ] + [
        (input, Contributor(cited_as='James Bond', agent=Person(name='James Bond', family_name='Bond', given_name='James')),)
        for input in [
            Contributor(cited_as='   \t James\n Bond \t     ', agent=Person(name='James  Bond')),
            Contributor(cited_as='', agent=Person(name='James  Bond')),
        ]
    ])
    def test_normalize_agentworkrelation(self, input, output, JsonLD):
        graph = MutableGraph.from_jsonld(JsonLD(input))
        Regulator().regulate(graph)
        assert graph.to_jsonld(in_edges=False) == JsonLD(output)
