import pytest
import rfc3987

import calendar

from share.normalize.links import DOILink, OrcidLink, DateParserLink


@pytest.mark.parametrize('date, result', [
    (None, ValueError('None is not a valid date.')),
    ('0059-11-01T00:00:00Z', ValueError('0059-11-01T00:00:00Z is before the lower bound 1200-01-01T00:00:00+00:00.')),
    ('20010101', '2001-01-01T00:00:00+00:00'),
    ('2013', '2013-01-01T00:00:00+00:00'),
    ('03:04, 19 Nov, 2014', '2014-11-19T03:04:00+00:00'),
    ('invalid date', ValueError('Unknown string format')),
    ('2001-1-01', '2001-01-01T00:00:00+00:00'),
    ('2001-2-30', ValueError('day is out of range for month')),
    ('14/2001', calendar.IllegalMonthError(14)),
    ('11/20/1990', '1990-11-20T00:00:00+00:00'),
    ('1990-11-20T00:00:00Z', '1990-11-20T00:00:00+00:00'),
    ('19 Nov, 2014', '2014-11-19T00:00:00+00:00'),
    ('Nov 2012', '2012-11-01T00:00:00+00:00'),
    ('January 1 2014', '2014-01-01T00:00:00+00:00'),
    ('3009-11-01T00:00:00Z', ValueError('3009-11-01T00:00:00Z is more than 100 years in the future.')),
    ('2016-01-01T15:03:04-05:00', '2016-01-01T20:03:04+00:00'),
    ('2016-01-01T15:03:04+5:00', '2016-01-01T10:03:04+00:00'),
    ('2016-01-01T15:03:04-3', '2016-01-01T18:03:04+00:00'),
    ('2016-01-01T15:03:04-3:30', '2016-01-01T18:33:04+00:00'),
    ('2016-01-01T15:03:04+99', ValueError('offset must be a timedelta strictly between -timedelta(hours=24) and timedelta(hours=24).')),
    # rolls over extra minutes
    ('2016-01-01T15:03:04-3:70', '2016-01-01T19:13:04+00:00'),
])
def test_dateparser_link(date, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            DateParserLink().execute(date)
        assert e.value.args == result.args
    else:
        assert DateParserLink().execute(date) == result


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
    ('10.517/ccdc.csd.cc1lj81f', ValueError('10.517/ccdc.csd.cc1lj81f is not a valid DOI')),
    ('10.517ccdc.csd.c>c1lj81f', ValueError('10.517ccdc.csd.c>c1lj81f is not a valid DOI')),
    ('10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('   10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('   10.5517/ccdc.csd.cc1lj81f   ', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('DOI:10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('doi:10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('The DOI is 10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('10.5517/ccdc.csd.cc1lj81f\n', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('https://dx.doi.org/10.1674/0003-0031(1998)140[0358:CAPWBS]2.0.CO;2', 'http://dx.doi.org/10.1674/0003-0031(1998)140%5B0358:CAPWBS%5D2.0.CO;2'),
    ('http://dx.doi.org/10.1002/1096-8644(200101)114:1<18::AID-AJPA1002>3.0.CO;2-2', 'http://dx.doi.org/10.1002/1096-8644(200101)114:1%3C18::AID-AJPA1002%3E3.0.CO;2-2'),
])
def test_doi_link(doi, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            DOILink().execute(doi)
        assert e.value.args == result.args
    else:
        assert rfc3987.parse(result)  # Extra URL validation
        assert DOILink().execute(doi) == result
