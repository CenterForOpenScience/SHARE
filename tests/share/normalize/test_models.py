import pytest

from share import models


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

    @pytest.mark.parametrize('input, output', [
        ('', []),
        ('foo', ['foo']),
        ('Foo', ['foo']),
        ('Foo; Bar', ['foo', 'bar']),
        ('        Foo       ', ['foo']),
        (' F\to\no ', ['f o o']),
        (' FOO BaR\n', ['foo bar']),
        ('FOO;bar,baz;', ['foo', 'bar', 'baz']),
        ('Crash, bandicoot', ['crash', 'bandicoot']),
        ('Cr   ash, \n\t\tba\nnd  icOOt', ['cr ash', 'ba nd icoot']),
        ('        \n\n\n\n\t\t\t\t', []),
        ('        \n\n;\n\n\t,\t\t\t', []),
    ])
    def test_normalize_tag(self, input, output):
        graph, node = FakeGraph([]), FakeNode({'name': input})

        models.Tag.normalize(node, graph)

        assert len(graph.added) == 0
        assert len(graph.removed) == 0
        assert set(x.attrs['name'] for x in graph.created) == set(output)
        assert len(graph.replaced) == 1
        assert graph.replaced[0][0].attrs['name'] == input
        assert set(x.attrs['name'] for x in graph.replaced[0][1]) == set(output)

    @pytest.mark.parametrize('input, output', [
        ({'name': 'Smith, J'}, {'name': 'J Smith', 'family_name': 'Smith', 'given_name': 'J'}),
        ({'name': 'J Smith'}, {'name': 'J Smith', 'family_name': 'Smith', 'given_name': 'J'}),
        ({'name': 'J    Smith   '}, {'name': 'J Smith', 'family_name': 'Smith', 'given_name': 'J'}),
        ({'name': 'Smith,     J'}, {'name': 'J Smith', 'family_name': 'Smith', 'given_name': 'J'}),
        ({'name': 'Johnathan James Doe'}, {'name': 'Johnathan James Doe', 'family_name': 'Doe', 'given_name': 'Johnathan', 'additional_name': 'James'}),
        ({'name': 'johnathan james doe'}, {'name': 'Johnathan James Doe', 'family_name': 'Doe', 'given_name': 'Johnathan', 'additional_name': 'James'}),
        ({'name': 'johnathan james doe JR'}, {'name': 'Johnathan James Doe Jr', 'family_name': 'Doe', 'given_name': 'Johnathan', 'additional_name': 'James', 'suffix': 'Jr'}),
        ({'given_name': 'J', 'family_name': 'Smith'}, {'name': 'J Smith', 'family_name': 'Smith', 'given_name': 'J'}),
        ({'given_name': '  J', 'family_name': '\n\nSmith'}, {'name': 'J Smith', 'family_name': 'Smith', 'given_name': 'J'}),
        ({'name': 'none'}, None),
        ({'name': ''}, None),
        ({'name': 'NULL'}, None),
        ({'name': 'None'}, None),
        ({'name': '           '}, None),
        ({'name': '     None      '}, None),
    ])
    def test_normalize_person(self, input, output):
        graph, node = FakeGraph([]), FakeNode(input)
        models.Person.normalize(node, graph)

        if output is None:
            assert node in graph.removed
        else:
            assert node.attrs == output

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
        (models.Creator, {'cited_as': '   \t James\n Bond \t     ', 'related': {'person': {'name': 'James   Bond'}, 'creative_work': {}}}, {'cited_as': 'James Bond'}),
        (models.Contributor, {'cited_as': '   \t James\n Bond \t     ', 'related': {'person': {'name': 'James   Bond'}, 'creative_work': {}}}, {'cited_as': 'James Bond'}),
        (models.Creator, {'cited_as': '', 'related': {'person': {'name': 'James   Bond'}, 'creative_work': {}}}, {'cited_as': 'James Bond'}),
        (models.Contributor, {'cited_as': '', 'related': {'person': {'name': 'James   Bond'}, 'creative_work': {}}}, {'cited_as': 'James Bond'}),
    ])
    def test_normalize_agentworkrelation(self, model, input, output):
        graph, node = FakeGraph([]), FakeNode(input)
        model.normalize(node, graph)

        if output is None:
            assert node in graph.removed
        else:
            assert node.attrs == output
