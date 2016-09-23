import pytest

from share.normalize.links import DOILink
from share.normalize.links import OrcidLink


@pytest.mark.parametrize('orcid, result', [
    (None, TypeError('None is not of type str')),
    ('', ValueError(' cannot be expressed as an orcid')),
    ('0000000346249680', 'https://orcid.org/0000-0003-4624-9680'),
    ('0000000317011251', 'https://orcid.org/0000-0003-1701-1251'),
    ('0000000229129030', 'https://orcid.org/0000-0002-2912-9030'),
    ('0000000248692412', ValueError('0000000248692412 is not a valid ORCID. Failed checksum')),
    ('0000000248692419', 'https://orcid.org/0000-0002-4869-2419'),
    ('0000-0002-4869-2419', 'https://orcid.org/0000-0002-4869-2419'),
    ('0000-0002-4869-2419', 'https://orcid.org/0000-0002-4869-2419'),
    ('https://orcid.org/0000-0002-1694-233X', 'https://orcid.org/0000-0002-1694-233X'),
    ('https://orcid.org/0000-0002-4869-2419', 'https://orcid.org/0000-0002-4869-2419'),
])
def test_orcid_link(orcid, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            OrcidLink().execute(orcid)
        assert e.value.args == result.args
    else:
        assert OrcidLink().execute(orcid) == result


@pytest.mark.parametrize('doi, result', [
    (None, TypeError('None is not of type str')),
    ('', ValueError(' is not a valid DOI')),
    ('105517/ccdc.csd.cc1lj81f', ValueError('105517/ccdc.csd.cc1lj81f is not a valid DOI')),
    ('0.5517/ccdc.csd.cc1lj81f', ValueError('0.5517/ccdc.csd.cc1lj81f is not a valid DOI')),
    ('10.5517ccdc.csd.cc1lj81f', ValueError('10.5517ccdc.csd.cc1lj81f is not a valid DOI')),
    ('10.517ccdc.csd.cc1lj81f', ValueError('10.517ccdc.csd.cc1lj81f is not a valid DOI')),
    ('10.517ccdc.csd.c>c1lj81f', ValueError('10.517ccdc.csd.c>c1lj81f is not a valid DOI')),
    ('10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('   10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('   10.5517/ccdc.csd.cc1lj81f   ', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('DOI:10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('doi:10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('The DOI is 10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('10.5517/ccdc.csd.cc1lj81f\n', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('https://dx.doi.org/10.1674/0003-0031(1998)140[0358:CAPWBS]2.0.CO;2', 'http://dx.doi.org/10.1674/0003-0031(1998)140[0358:CAPWBS]2.0.CO;2'),
])
def test_doi_link(doi, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            DOILink().execute(doi)
        assert e.value.args == result.args
    else:
        assert DOILink().execute(doi) == result
