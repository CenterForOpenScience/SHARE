import pytest

from share.legacy_normalize.regulate.steps.normalize_iris import NormalizeIRIs
from share.util.graph import MutableGraph


class TestNormalizeIRIsStep:
    @pytest.mark.parametrize('schemes, authorities, expected_identifiers', [
        ([], [], 4),
        (['mailto'], [], 3),
        (['mailto', 'http'], [], 1),
        ([], ['issn'], 3),
        ([], ['osf.io', 'foo'], 3),
        (['nothing'], ['everything'], 4),
        (['http'], ['example.com', 'issn'], 0),
    ])
    def test_blocks(self, schemes, authorities, expected_identifiers):
        identifiers = [
            # (uri, scheme, authority)
            ('http://osf.io/mst3k/', 'http', 'osf.io'),
            ('mailto:foo@example.com', 'mailto', 'example.com'),
            ('2049-3630', 'urn', 'issn'),
            ('0000-0002-1825-0097', 'http', 'orcid.org'),
        ]

        step = NormalizeIRIs(blocked_schemes=schemes, blocked_authorities=authorities)
        graph = MutableGraph()

        for uri, scheme, authority in identifiers:
            node = graph.add_node('id_{}'.format(authority), 'workidentifier', {'uri': uri})
            assert node['scheme'] is None
            assert node['host'] is None

            step.regulate_node(node)

            if scheme not in schemes and authority not in authorities:
                assert node['scheme'] == scheme
                assert node['host'] == authority

        assert len(graph.filter_type('workidentifier')) == expected_identifiers

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
    def test_normalize_agentidentifier(self, input, output):
        graph = MutableGraph()
        node = graph.add_node('1', 'agentidentifier', {'uri': input})
        NormalizeIRIs().regulate_node(node)
        if output:
            assert node['uri'] == output
        else:
            assert len(graph) == 0

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
        ('http://arxiv.org/index.php?view&amp;id=12', 'http://arxiv.org/index.php?view&id=12'),
        ('10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
        ('   arxiv:1212.20282    ', 'http://arxiv.org/abs/1212.20282'),
        ('oai:subdomain.cos.io:this.is.stuff', 'oai://subdomain.cos.io/this.is.stuff'),
        ('Beau, R <http://researchonline.lshtm.ac.uk/view/creators/999461.html>;  Douglas, I <http://researchonline.lshtm.ac.uk/view/creators/103524.html>;  Evans, S <http://researchonline.lshtm.ac.uk/view/creators/101520.html>;  Clayton, T <http://researchonline.lshtm.ac.uk/view/creators/11213.html>;  Smeeth, L <http://researchonline.lshtm.ac.uk/view/creators/13212.html>;      (2011) How Long Do Children Stay on Antiepileptic Treatments in the UK?  [Conference or Workshop Item]', None),
    ])
    def test_normalize_workidentifier(self, input, output):
        graph = MutableGraph()
        node = graph.add_node('1', 'workidentifier', {'uri': input})
        step = NormalizeIRIs(blocked_schemes=['mailto'], blocked_authorities=['issn', 'orcid.org'])
        step.regulate_node(node)
        if output:
            assert node['uri'] == output
        else:
            assert len(graph) == 0

    def test_error_on_bad_settings(self):
        with pytest.raises(TypeError):
            NormalizeIRIs(bad_setting=True)

        # No required settings
        NormalizeIRIs()
