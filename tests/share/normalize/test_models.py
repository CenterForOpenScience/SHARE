import pytest

from share.change import ChangeGraph

from tests.share.normalize.factories import Tag, CreativeWork, Person, WorkIdentifier, Agent, Institution, Organization, AgentIdentifier, Creator, Contributor


class TestModelNormalization:

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
    def test_normalize_tag(self, input, output, Graph):
        graph = ChangeGraph(Graph(CreativeWork(tags=[input])), disambiguate=False)
        graph.normalize()

        assert [n.serialize() for n in sorted(graph.nodes, key=lambda x: x.type + str(x.id))] == Graph(CreativeWork(tags=output))

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
    def test_normalize_person(self, input, output, Graph):
        graph = ChangeGraph(Graph(input), disambiguate=False)
        graph.normalize()
        assert graph.serialize() == (Graph(output) if output else [])

    # test two people with the same identifier are merged
    # sort by length and then alphabetize name field
    @pytest.mark.parametrize('input, output', [
        # same name, same identifier
        ([
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)])
        ], [Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)])]),
        # same name, different identifiers
        ([
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(2)])
        ], [
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(2)])
        ]),
        # no name - name, same identifier
        ([
            Person(name='', identifiers=[AgentIdentifier(1)]),
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)])
        ], [Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)])]),
        # two names, same identifier, take longer name
        ([
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='Barbra Dylan', identifiers=[AgentIdentifier(1)])
        ], [Person(name='Barbra Dylan', identifiers=[AgentIdentifier(1)])]),
        # two sames, same length, same identifier, alphabetize and take first
        ([
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='Aarb Dylan', identifiers=[AgentIdentifier(1)])
        ], [Person(name='Aarb Dylan', identifiers=[AgentIdentifier(1)])]),
        # 3 different names, take longest of each name field
        ([
            Person(name='Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='Barb Dylan', identifiers=[AgentIdentifier(1)]),
            Person(name='B. D. Dylan', identifiers=[AgentIdentifier(1)])
        ], [Person(name='Barb D. Dylan', identifiers=[AgentIdentifier(1)])]),
    ])
    def test_normalize_person_relation(self, input, output, Graph):
        graph = ChangeGraph(Graph(CreativeWork(related_agents=input)))
        graph.normalize()
        assert [n.serialize() for n in graph.nodes] == Graph(CreativeWork(related_agents=output))

    @pytest.mark.parametrize('input, output', [
        (Agent(name='none'), None),
        (Agent(name=''), None),
        (Agent(name='NULL'), None),
        (Agent(name='None'), None),
        (Agent(name='           '), None),
        (Agent(name='     None      '), None),
        (Agent(name='University \n of Arizona '), Institution(name='University of Arizona')),
        (Agent(name='NMRC, University College, Cork, Ireland'), Institution(name='NMRC, University College', location='Cork, Ireland')),
        (Agent(name='Ioffe Physico-Technical Institute'), Institution(name='Ioffe Physico-Technical Institute')),
        (Agent(name='DPTA'), Organization(name='DPTA')),
        (Agent(name='B. Verkin Institute for Low Temperatures Physics & Engineering, Kharkov, Ukraine'), Institution(name='B. Verkin Institute for Low Temperatures Physics & Engineering', location='Kharkov, Ukraine', type='institution')),
        (Agent(name='Physikalisches Institut, University Wuerzburg, Germany'), Agent(name='Physikalisches Institut', location='University Wuerzburg, Germany', type='institution')),
        (Agent(name='Centro de Biotecnologia e Departamento de Biofísica; UFRGS; Av Bento Goncalves 9500, Predio 43431 sala 213 91501-970 Porto Alegre Rio Grande do Sul Brazi'), Agent(name='UFRGS - Centro de Biotecnologia e Departamento de Biofísica', location='Av Bento Goncalves 9500, Predio 43431 sala 213 91501-970 Porto Alegre Rio Grande do Sul Brazi')),
        (Agent(name='Department of Chemistry; ZheJiang University; HangZhou ZheJiang CHINA'), Institution(name='ZheJiang University - Department of Chemistry', location='HangZhou ZheJiang CHINA')),
        (Agent(name='Marine Evolution and Conservation; Groningen Institute for Evolutionary Life Sciences; University of Groningen; Nijenborgh 7, 9747 AG Groningen The Netherlands'), Institution(name='University of Groningen - Marine Evolution and Conservation; Groningen Institute for Evolutionary Life Sciences', location='Nijenborgh 7, 9747 AG Groningen The Netherlands')),
        (Agent(name='Institute of Marine Research; PO Box 1870 Nordnes, 5817 Bergen Norway'), Institution(name='Institute of Marine Research', location='PO Box 1870 Nordnes, 5817 Bergen Norway')),
        (Agent(name='    PeerJ    Inc.    '), Organization(name='PeerJ Inc.')),
        (Agent(name=' Clinton   Foundation\n   '), Organization(name='Clinton Foundation')),
    ])
    def test_normalize_agent(self, input, output, Graph):
        graph = ChangeGraph(Graph(input), disambiguate=False)
        graph.normalize()
        assert graph.serialize() == (Graph(output) if output else [])

    # test two agents with the same name are merged
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
            Organization(name='University of Virginia', identifiers=[AgentIdentifier(1)]),
            Institution(name='University of Virginia', identifiers=[AgentIdentifier(1)])
        ], [Institution(name='University of Virginia', identifiers=[AgentIdentifier(1)])]),
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
    def test_normalize_agent_relation(self, input, output, Graph):
        graph = ChangeGraph(Graph(CreativeWork(related_agents=input)))
        graph.normalize()
        assert [n.serialize() for n in graph.nodes] == Graph(CreativeWork(related_agents=output))

    @pytest.mark.parametrize('input, output', [
        ({'title': '', 'description': ''}, {'title': '', 'description': ''}),
        ({'title': '    ', 'description': '     '}, {'title': '', 'description': ''}),
        ({'title': 'Title\nLine'}, {'title': 'Title Line'}),
        ({'description': 'Line\nAfter\nLine\nAfter\nLine'}, {'description': 'Line After Line After Line'}),
    ])
    def test_normalize_creativework(self, input, output, Graph):
        graph = ChangeGraph(Graph(CreativeWork(**input)), disambiguate=False)
        graph.normalize()
        assert graph.serialize() == Graph(CreativeWork(**output))

    @pytest.mark.parametrize('input, output', [
        ('', None),
        ('htp://google.com', None),
        ('blackmagic://goat.hooves', None),
        ('1476-4687 ', None),
        ('urn://issn/1476-4687', None),
        ('0000000248692412', None),
        ('https://orcid.org/0000-0002-1694-233X', None),
        ('aperson@dinosaurs.sexy', None),
        ('10.517ccdc.csd.c>c1lj81f', None),
        ('10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
        ('   arxiv:1212.20282    ', 'http://arxiv.org/abs/1212.20282'),
        ('oai:subdomain.cos.io:this.is.stuff', 'oai://subdomain.cos.io/this.is.stuff'),
        ('Beau, R <http://researchonline.lshtm.ac.uk/view/creators/999461.html>;  Douglas, I <http://researchonline.lshtm.ac.uk/view/creators/103524.html>;  Evans, S <http://researchonline.lshtm.ac.uk/view/creators/101520.html>;  Clayton, T <http://researchonline.lshtm.ac.uk/view/creators/11213.html>;  Smeeth, L <http://researchonline.lshtm.ac.uk/view/creators/13212.html>;      (2011) How Long Do Children Stay on Antiepileptic Treatments in the UK?  [Conference or Workshop Item]', None),
    ])
    def test_normalize_workidentifier(self, input, output, Graph):
        graph = ChangeGraph(Graph(WorkIdentifier(uri=input)), disambiguate=False)
        graph.normalize()
        assert graph.serialize() == (Graph(WorkIdentifier(uri=output, parse=True)) if output else [])

    @pytest.mark.parametrize('input, output', [
        ('', None),
        ('             ', None),
        ('0000000248692412', None),
        ('000000000248692419', None),
        ('urn://issn/1476-4687', 'urn://issn/1476-4687'),
        ('0000000248692419', 'http://orcid.org/0000-0002-4869-2419'),
        ('0000-0002-4869-2419', 'http://orcid.org/0000-0002-4869-2419'),
        ('0000-0002-4869-2419', 'http://orcid.org/0000-0002-4869-2419'),
        ('Beau, R <http://researchonline.lshtm.ac.uk/view/creators/999461.html>;  Douglas, I <http://researchonline.lshtm.ac.uk/view/creators/103524.html>;  Evans, S <http://researchonline.lshtm.ac.uk/view/creators/101520.html>;  Clayton, T <http://researchonline.lshtm.ac.uk/view/creators/11213.html>;  Smeeth, L <http://researchonline.lshtm.ac.uk/view/creators/13212.html>;      (2011) How Long Do Children Stay on Antiepileptic Treatments in the UK?  [Conference or Workshop Item]', None),
    ])
    def test_normalize_agentidentifier(self, input, output, Graph):
        graph = ChangeGraph(Graph(AgentIdentifier(uri=input)), disambiguate=False)
        graph.normalize()
        assert graph.serialize() == (Graph(AgentIdentifier(uri=output, parse=True)) if output else [])

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
    def test_normalize_agentworkrelation(self, input, output, Graph):
        graph = ChangeGraph(Graph(input))
        graph.normalize()
        assert graph.serialize() == Graph(output)
