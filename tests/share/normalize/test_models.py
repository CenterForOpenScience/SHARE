import pytest

from share import models
from share.change import ChangeGraph

from tests.share.normalize.factories import Tag, CreativeWork, Person


class FakeNode:

    def __init__(self, attrs):
        self.attrs = attrs
        self.relations = attrs.pop('related', {})

    def related(self, name):
        if name not in self.relations:
            return None
        return FakeNode(self.relations[name])


class FakeGraph:
    def __init__(self, nodes):
        self.added = []
        self.removed = []
        self.created = []
        self.replaced = []

    def remove(self, node):
        self.removed.append(node)

    def add(self, node):
        self.added.append(node)

    def create(self, attrs):
        n = FakeNode(attrs)
        self.created.append(n)
        return n

    def replace(self, source, *targets):
        self.replaced.append((source, targets))


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
        graph = ChangeGraph(Graph(CreativeWork(tags=[input])))
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
        graph = ChangeGraph(Graph(input))
        graph.normalize()
        assert [n.serialize() for n in graph.nodes] == (Graph(output) if output else [])

    @pytest.mark.parametrize('input, output', [
        ({'name': 'none'}, None),
        ({'name': ''}, None),
        ({'name': 'NULL'}, None),
        ({'name': 'None'}, None),
        ({'name': '           '}, None),
        ({'name': '     None      '}, None),
        ({'name': 'University \n of Arizona '}, {'name': 'University of Arizona', 'type': 'institution'}),
        ({'name': 'NMRC, University College, Cork, Ireland'}, {'name': 'NMRC, University College', 'location': 'Cork, Ireland', 'type': 'institution'}),
        ({'name': 'Ioffe Physico-Technical Institute'}, {'name': 'Ioffe Physico-Technical Institute', 'type': 'institution'}),
        ({'name': 'DPTA'}, {'name': 'DPTA', 'type': 'organization'}),
        ({'name': 'B. Verkin Institute for Low Temperatures Physics & Engineering, Kharkov, Ukraine'}, {'name': 'B. Verkin Institute for Low Temperatures Physics & Engineering', 'location': 'Kharkov, Ukraine', 'type': 'institution'}),
        ({'name': 'Physikalisches Institut, University Wuerzburg, Germany'}, {'name': 'Physikalisches Institut', 'location': 'University Wuerzburg, Germany', 'type': 'institution'}),
        ({'name': 'Centro de Biotecnologia e Departamento de Biofísica; UFRGS; Av Bento Goncalves 9500, Predio 43431 sala 213 91501-970 Porto Alegre Rio Grande do Sul Brazi'}, {'name': 'UFRGS - Centro de Biotecnologia e Departamento de Biofísica', 'location': 'Av Bento Goncalves 9500, Predio 43431 sala 213 91501-970 Porto Alegre Rio Grande do Sul Brazi', 'type': 'agent'}),
        ({'name': 'Department of Chemistry; ZheJiang University; HangZhou ZheJiang CHINA'}, {'name': 'ZheJiang University - Department of Chemistry', 'location': 'HangZhou ZheJiang CHINA', 'type': 'institution'}),
        ({'name': 'Marine Evolution and Conservation; Groningen Institute for Evolutionary Life Sciences; University of Groningen; Nijenborgh 7, 9747 AG Groningen The Netherlands'}, {'name': 'University of Groningen - Marine Evolution and Conservation; Groningen Institute for Evolutionary Life Sciences', 'location': 'Nijenborgh 7, 9747 AG Groningen The Netherlands', 'type': 'institution'}),
        ({'name': 'Institute of Marine Research; PO Box 1870 Nordnes, 5817 Bergen Norway'}, {'name': 'Institute of Marine Research', 'location': 'PO Box 1870 Nordnes, 5817 Bergen Norway', 'type': 'institution'}),
        ({'name': '    PeerJ    Inc.    '}, {'name': 'PeerJ Inc.', 'type': 'organization'}),
        ({'name': ' Clinton   Foundation\n   '}, {'name': 'Clinton Foundation', 'type': 'organization'}),
    ])
    def test_normalize_agent(self, input, output):
        graph, node = FakeGraph([]), FakeNode(input)
        node.type = 'agent'
        models.Agent.normalize(node, graph)

        if output is None:
            assert node in graph.removed
        else:
            assert node.type == output.pop('type', 'agent')
            assert node.attrs == output

    @pytest.mark.parametrize('input, output', [
        ({'title': '', 'description': ''}, {'title': '', 'description': ''}),
        ({'title': '    ', 'description': '     '}, {'title': '', 'description': ''}),
        ({'title': 'Title\nLine'}, {'title': 'Title Line'}),
        ({'description': 'Line\nAfter\nLine\nAfter\nLine'}, {'description': 'Line After Line After Line'}),
    ])
    def test_normalize_creativework(self, input, output):
        node = FakeNode(input)
        models.AbstractCreativeWork.normalize(node, None)
        assert node.attrs == output

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
    def test_normalize_workidentifier(self, input, output):
        graph, node = FakeGraph([]), FakeNode({'uri': input})
        models.WorkIdentifier.normalize(node, graph)

        if output is None:
            assert node in graph.removed
        else:
            assert node.attrs['uri'] == output

    @pytest.mark.parametrize('input, output', [
        ('', None),
        ('             ', None),
        ('0000000248692412', None),
        ('000000000248692419', None),
        ('0000000248692419', 'http://orcid.org/0000-0002-4869-2419'),
        ('0000-0002-4869-2419', 'http://orcid.org/0000-0002-4869-2419'),
        ('0000-0002-4869-2419', 'http://orcid.org/0000-0002-4869-2419'),
        ('Beau, R <http://researchonline.lshtm.ac.uk/view/creators/999461.html>;  Douglas, I <http://researchonline.lshtm.ac.uk/view/creators/103524.html>;  Evans, S <http://researchonline.lshtm.ac.uk/view/creators/101520.html>;  Clayton, T <http://researchonline.lshtm.ac.uk/view/creators/11213.html>;  Smeeth, L <http://researchonline.lshtm.ac.uk/view/creators/13212.html>;      (2011) How Long Do Children Stay on Antiepileptic Treatments in the UK?  [Conference or Workshop Item]', None),
    ])
    def test_normalize_agentidentifier(self, input, output):
        graph, node = FakeGraph([]), FakeNode({'uri': input})
        models.AgentIdentifier.normalize(node, graph)

        if output is None:
            assert node in graph.removed
        else:
            assert node.attrs['uri'] == output

    @pytest.mark.parametrize('model, input, output', [
        (models.Creator, {'cited_as': '   \t James\n Bond \t     ', 'related': {'agent': {'name': 'James   Bond'}, 'creative_work': {}}}, {'cited_as': 'James Bond'}),
        (models.Contributor, {'cited_as': '   \t James\n Bond \t     ', 'related': {'agent': {'name': 'James   Bond'}, 'creative_work': {}}}, {'cited_as': 'James Bond'}),
        (models.Creator, {'cited_as': '', 'related': {'agent': {'name': 'James   Bond'}, 'creative_work': {}}}, {'cited_as': 'James Bond'}),
        (models.Contributor, {'cited_as': '', 'related': {'agent': {'name': 'James   Bond'}, 'creative_work': {}}}, {'cited_as': 'James Bond'}),
    ])
    def test_normalize_agentworkrelation(self, model, input, output):
        graph, node = FakeGraph([]), FakeNode(input)
        model.normalize(node, graph)

        if output is None:
            assert node in graph.removed
        else:
            assert node.attrs == output
