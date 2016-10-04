import pytest
import rfc3987
import calendar
import pendulum

from share.normalize.links import DOILink
from share.normalize.links import IRILink
from share.normalize.links import ISNILink
from share.normalize.links import ISSNLink
from share.normalize.links import OrcidLink

UPPER_BOUND = pendulum.today().add(years=100).isoformat()


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
    ('3009-11-01T00:00:00Z', ValueError('3009-11-01T00:00:00Z is after the upper bound ' + UPPER_BOUND + '.')),
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


@pytest.mark.parametrize('issn, result', [
    ('0378-5955', 'urn://issn/0378-5955'),
    ('1534-0481', 'urn://issn/1534-0481'),
    ('1476-4687', 'urn://issn/1476-4687'),
    ('0028-0836', 'urn://issn/0028-0836'),
    ('1144-875x', 'urn://issn/1144-875X'),
    ('1144-875X', 'urn://issn/1144-875X'),
    ('0378-5950', ValueError('\'03785950\' is not a valid ISSN; failed checksum.')),
    ('0000-0002-4869-2419', ValueError('\'0000-0002-4869-2419\' cannot be expressed as an ISSN.')),
])
def test_issn_link(issn, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            ISSNLink().execute(issn)
        assert e.value.args == result.args
    else:
        assert ISSNLink().execute(issn)['IRI'] == result


@pytest.mark.parametrize('isni, result', [
    (None, TypeError('\'None\' is not of type str.')),
    ('', ValueError('\'\' cannot be expressed as an ISNI.')),
    ('0000000121032683', 'http://isni.org/0000000121032683'),
    ('0000000346249680', ValueError('\'0000000346249680\' is outside reserved ISNI range.')),
    ('0000-0001-2103-2683', 'http://isni.org/0000000121032683'),
    ('http://isni.org/0000000121032683', 'http://isni.org/0000000121032683'),
    ('000000012150090X', 'http://isni.org/000000012150090X'),
    ('000000012150090x', 'http://isni.org/000000012150090X'),
    ('0000-0001-2150-090X', 'http://isni.org/000000012150090X'),
    ('0000-0001-2150-090x', 'http://isni.org/000000012150090X'),
])
def test_isni_link(isni, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            ISNILink().execute(isni)
        assert e.value.args == result.args
    else:
        assert ISNILink().execute(isni)['IRI'] == result


@pytest.mark.parametrize('orcid, result', [
    (None, TypeError('\'None\' is not of type str.')),
    ('', ValueError('\'\' cannot be expressed as an ORCID.')),
    ('0000000346249680', 'http://orcid.org/0000-0003-4624-9680'),
    ('0000000317011251', 'http://orcid.org/0000-0003-1701-1251'),
    ('0000000229129030', 'http://orcid.org/0000-0002-2912-9030'),
    ('0000000248692412', ValueError('\'0000000248692412\' is not a valid ORCID; failed checksum.')),
    ('0000000248692419', 'http://orcid.org/0000-0002-4869-2419'),
    ('0000-0002-4869-2419', 'http://orcid.org/0000-0002-4869-2419'),
    ('0000-0002-4869-2419', 'http://orcid.org/0000-0002-4869-2419'),
    ('https://orcid.org/0000-0002-1694-233X', 'http://orcid.org/0000-0002-1694-233X'),
    ('https://orcid.org/0000-0002-4869-2419', 'http://orcid.org/0000-0002-4869-2419'),
    ('0000-0001-2150-090X', ValueError('\'000000012150090X\' is outside reserved ORCID range.')),
])
def test_orcid_link(orcid, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            OrcidLink().execute(orcid)
        assert e.value.args == result.args
    else:
        assert OrcidLink().execute(orcid)['IRI'] == result


@pytest.mark.parametrize('doi, result', [
    (None, TypeError('\'None\' is not of type str.')),
    ('', ValueError('\'\' is not a valid DOI.')),
    ('105517/ccdc.csd.cc1lj81f', ValueError('\'105517/ccdc.csd.cc1lj81f\' is not a valid DOI.')),
    ('0.5517/ccdc.csd.cc1lj81f', ValueError('\'0.5517/ccdc.csd.cc1lj81f\' is not a valid DOI.')),
    ('10.5517ccdc.csd.cc1lj81f', ValueError('\'10.5517ccdc.csd.cc1lj81f\' is not a valid DOI.')),
    ('10.517ccdc.csd.cc1lj81f', ValueError('\'10.517ccdc.csd.cc1lj81f\' is not a valid DOI.')),
    ('10.517/ccdc.csd.cc1lj81f', ValueError('\'10.517/ccdc.csd.cc1lj81f\' is not a valid DOI.')),
    ('10.517ccdc.csd.c>c1lj81f', ValueError('\'10.517ccdc.csd.c>c1lj81f\' is not a valid DOI.')),
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
        assert DOILink().execute(doi)['IRI'] == result


class TestIRILink:

    def _do_test(self, input, output):
        if isinstance(output, Exception):
            with pytest.raises(type(output)) as e:
                IRILink().execute(input)
            assert e.value.args == output.args
        else:
            assert {k: v for k, v in IRILink().execute(input).items() if k in output} == output

    @pytest.mark.parametrize('input, output', [
        ('trexy@dinosaurs.sexy', {
            'scheme': 'mailto',
            'authority': 'dinosaurs.sexy',
            'IRI': 'mailto:trexy@dinosaurs.sexy',
        }),
        ('mailto:trexy@dinosaurs.sexy', {
            'scheme': 'mailto',
            'authority': 'dinosaurs.sexy',
            'IRI': 'mailto:trexy@dinosaurs.sexy',
        }),
        ('mailto:trexy@dinosaurs.sexy?subject=Dinosaurs', {
            'scheme': 'mailto',
            'authority': 'dinosaurs.sexy',
            'IRI': 'mailto:trexy@dinosaurs.sexy',
        }),
    ])
    def test_emails(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input, output', [
        ('https://google.com/', {
            'scheme': 'http',
            'authority': 'google.com',
            'IRI': 'http://google.com/',
        }),
        ('https://GOOGLE.com/', {
            'scheme': 'http',
            'authority': 'google.com',
            'IRI': 'http://google.com/',
        }),
        ('https://GOOGLE.com/MixedCases', {
            'scheme': 'http',
            'authority': 'google.com',
            'IRI': 'http://google.com/MixedCases',
        }),
        ('https://GOOGLE.com:80/MixedCases', {
            'scheme': 'http',
            'authority': 'google.com',
            'IRI': 'http://google.com/MixedCases',
        }),
        ('https://GOOGLE.com:443/MixedCases', {
            'scheme': 'http',
            'authority': 'google.com',
            'IRI': 'http://google.com/MixedCases',
        }),
    ])
    def test_urls(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input, output', [
        ('10.5517/aadc.csd.cc1lj81f', {
            'scheme': 'http',
            'authority': 'dx.doi.org',
            'IRI': 'http://dx.doi.org/10.5517/AADC.CSD.CC1LJ81F',
        }),
        ('   10.5517/bbdc.csd.cc1lj81f', {
            'scheme': 'http',
            'authority': 'dx.doi.org',
            'IRI': 'http://dx.doi.org/10.5517/BBDC.CSD.CC1LJ81F',
        }),
        ('     10.5517/ccdc.csd.cc1lj81f     ', {
            'scheme': 'http',
            'authority': 'dx.doi.org',
            'IRI': 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F',
        }),
        ('DOI:10.5517/dddc.csd.cc1lj81f', {
            'scheme': 'http',
            'authority': 'dx.doi.org',
            'IRI': 'http://dx.doi.org/10.5517/DDDC.CSD.CC1LJ81F',
        }),
        ('doi:10.5517/eedc.csd.cc1lj81f', {
            'scheme': 'http',
            'authority': 'dx.doi.org',
            'IRI': 'http://dx.doi.org/10.5517/EEDC.CSD.CC1LJ81F',
        }),
        ('The DOI is 10.5517/ffdc.csd.cc1lj81f', {
            'scheme': 'http',
            'authority': 'dx.doi.org',
            'IRI': 'http://dx.doi.org/10.5517/FFDC.CSD.CC1LJ81F',
        }),
        ('10.5517/ggdc.csd.cc1lj81f\n', {
            'scheme': 'http',
            'authority': 'dx.doi.org',
            'IRI': 'http://dx.doi.org/10.5517/GGDC.CSD.CC1LJ81F',
        }),
        ('https://dx.doi.org/10.1674/0003-0031(1998)140[0358:CAPWBS]2.0.CO;2', {
            'scheme': 'http',
            'authority': 'dx.doi.org',
            'IRI': 'http://dx.doi.org/10.1674/0003-0031(1998)140%5B0358:CAPWBS%5D2.0.CO;2',
        }),
        ('http://dx.doi.org/10.1002/1096-8644(200101)114:1<18::AID-AJPA1002>3.0.CO;2-2', {
            'scheme': 'http',
            'authority': 'dx.doi.org',
            'IRI': 'http://dx.doi.org/10.1002/1096-8644(200101)114:1%3C18::AID-AJPA1002%3E3.0.CO;2-2',
        }),
    ])
    def test_dois(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input, output', [
        ('0000000346249680', {
            'scheme': 'http',
            'authority': 'orcid.org',
            'IRI': 'http://orcid.org/0000-0003-4624-9680',
        }),
        ('0000000317011251', {
            'scheme': 'http',
            'authority': 'orcid.org',
            'IRI': 'http://orcid.org/0000-0003-1701-1251',
        }),
        ('0000000229129030', {
            'scheme': 'http',
            'authority': 'orcid.org',
            'IRI': 'http://orcid.org/0000-0002-2912-9030',
        }),
        ('0000000248692419', {
            'scheme': 'http',
            'authority': 'orcid.org',
            'IRI': 'http://orcid.org/0000-0002-4869-2419',
        }),
        ('0000-0002-4869-2419', {
            'scheme': 'http',
            'authority': 'orcid.org',
            'IRI': 'http://orcid.org/0000-0002-4869-2419',
        }),
        ('0000-0002-4869-2419', {
            'scheme': 'http',
            'authority': 'orcid.org',
            'IRI': 'http://orcid.org/0000-0002-4869-2419',
        }),
        ('http://orcid.org/0000-0002-1694-233X', {
            'scheme': 'http',
            'authority': 'orcid.org',
            'IRI': 'http://orcid.org/0000-0002-1694-233X',
        }),
        ('http://orcid.org/0000-0002-1694-233x', {
            'scheme': 'http',
            'authority': 'orcid.org',
            'IRI': 'http://orcid.org/0000-0002-1694-233X',
        }),
        ('http://orcid.org/0000-0002-4869-2419', {
            'scheme': 'http',
            'authority': 'orcid.org',
            'IRI': 'http://orcid.org/0000-0002-4869-2419',
        }),
    ])
    def test_orcids(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input, output', [
        ('0000000121032683', {
            'scheme': 'http',
            'authority': 'isni.org',
            'IRI': 'http://isni.org/0000000121032683'
        }),
        ('0000-0001-2103-2683', {
            'scheme': 'http',
            'authority': 'isni.org',
            'IRI': 'http://isni.org/0000000121032683'
        }),
        ('http://isni.org/0000000121032683', {
            'scheme': 'http',
            'authority': 'isni.org',
            'IRI': 'http://isni.org/0000000121032683'
        }),
        ('000000012150090X', {
            'scheme': 'http',
            'authority': 'isni.org',
            'IRI': 'http://isni.org/000000012150090X',
        }),
        ('000000012150090x', {
            'scheme': 'http',
            'authority': 'isni.org',
            'IRI': 'http://isni.org/000000012150090X',
        }),
        ('0000-0001-2150-090X', {
            'scheme': 'http',
            'authority': 'isni.org',
            'IRI': 'http://isni.org/000000012150090X',
        }),
        ('0000-0001-2150-090x', {
            'scheme': 'http',
            'authority': 'isni.org',
            'IRI': 'http://isni.org/000000012150090X',
        }),
    ])
    def test_isnis(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input, output', [
        (None, TypeError('\'None\' is not of type str.')),
        ('', ValueError('\'\' could not be identified as an Identifier.')),
        ('105517/ccdc.csd.cc1lj81f', ValueError('\'105517/ccdc.csd.cc1lj81f\' is not a valid \'absolute_IRI\'.')),
        ('0.5517/ccdc.csd.cc1lj81f', ValueError('\'0.5517/ccdc.csd.cc1lj81f\' is not a valid \'absolute_IRI\'.')),
        ('10.5517ccdc.csd.cc1lj81f', ValueError('\'10.5517ccdc.csd.cc1lj81f\' is not a valid DOI.')),
        ('10.517ccdc.csd.cc1lj81f', ValueError('\'10.517ccdc.csd.cc1lj81f\' is not a valid DOI.')),
        ('10.517/ccdc.csd.cc1lj81f', ValueError('\'10.517/ccdc.csd.cc1lj81f\' is not a valid DOI.')),
        ('10.517ccdc.csd.c>c1lj81f', ValueError('\'10.517ccdc.csd.c>c1lj81f\' is not a valid DOI.')),
        ('0000000248692412', ValueError('\'0000000248692412\' could not be identified as an Identifier.')),
        ('0000000000000000', ValueError('\'0000000000000000\' could not be identified as an Identifier.')),
    ])
    def test_malformed(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input', [
        '10.5517/ggdc.csd.cc1lj81f',
        'The DOI is 10.5517/ffdc.csd.cc1lj81f',
        'https://dx.doi.org/10.1674/0003-0031(1998)140[0358:CAPWBS]2.0.CO;2',
        'https://orcid.org/0000-0002-1694-233X',
        '0000-0002-4869-2419',
        '0000000317011251',
        'trexy@dinosaurs.sexy',
        'mailto:trexy@dinosaurs.sexy',
        '0000-0001-2150-090X',
    ])
    def test_benchmark(self, input, benchmark):
        benchmark(IRILink().execute, input)
