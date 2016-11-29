import pytest
import rfc3987
import calendar
import pendulum

from share.normalize.links import ARKLink
from share.normalize.links import ArXivLink
from share.normalize.links import DOILink
from share.normalize.links import DateParserLink
from share.normalize.links import GuessAgentTypeLink
from share.normalize.links import IRILink
from share.normalize.links import ISNILink
from share.normalize.links import ISSNLink
from share.normalize.links import InfoURILink
from share.normalize.links import OrcidLink
from share.normalize.links import URNLink

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
    ('000000000248692419', ValueError('\'000000000248692419\' cannot be expressed as an ORCID.')),
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
    ('http://www.scirp.org/journal/PaperDownload.aspx?DOI=10.4236/wjcd.2016.69035', ValueError('\'http://www.scirp.org/journal/PaperDownload.aspx?DOI=10.4236/wjcd.2016.69035\' is not a valid DOI.')),
    ('10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('   10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('   10.5517/ccdc.csd.cc1lj81f   ', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('DOI:10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('doi:10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('The DOI is 10.5517/ccdc.csd.cc1lj81f', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('10.5517/ccdc.csd.cc1lj81f\n', 'http://dx.doi.org/10.5517/CCDC.CSD.CC1LJ81F'),
    ('https://dx.doi.org/10.1674/0003-0031(1998)140[0358:CAPWBS]2.0.CO;2', 'http://dx.doi.org/10.1674/0003-0031(1998)140%5B0358:CAPWBS%5D2.0.CO;2'),
    ('http://dx.doi.org/10.1002/1096-8644(200101)114:1<18::AID-AJPA1002>3.0.CO;2-2', 'http://dx.doi.org/10.1002/1096-8644(200101)114:1%3C18::AID-AJPA1002%3E3.0.CO;2-2'),
    ('10.18142/8', 'http://dx.doi.org/10.18142/8'),
    ('10.3389%2Ffpls.2014.00388', 'http://dx.doi.org/10.3389/FPLS.2014.00388'),
])
def test_doi_link(doi, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            DOILink().execute(doi)
        assert e.value.args == result.args
    else:
        assert rfc3987.parse(result)  # Extra URL validation
        assert DOILink().execute(doi)['IRI'] == result


@pytest.mark.parametrize('arxiv_id, result', [
    (None, TypeError('\'None\' is not of type str.')),
    ('', ValueError('\'\' is not a valid ArXiv Identifier.')),
    ('arXiv:1023..20382', ValueError('\'arXiv:1023..20382\' is not a valid ArXiv Identifier.')),
    ('something else', ValueError('\'something else\' is not a valid ArXiv Identifier.')),
    ('arXiv//1234.34543', ValueError('\'arXiv//1234.34543\' is not a valid ArXiv Identifier.')),
    ('arXiv:101022232', ValueError('\'arXiv:101022232\' is not a valid ArXiv Identifier.')),
    ('arXiv:10102.22322', ValueError('\'arXiv:10102.22322\' is not a valid ArXiv Identifier.')),
    ('arXiv:2.2', ValueError('\'arXiv:2.2\' is not a valid ArXiv Identifier.')),
    ('arxiv:1212.20282', 'http://arxiv.org/abs/1212.20282'),
    ('   arxiv:1212.20282', 'http://arxiv.org/abs/1212.20282'),
    ('   arxiv:1212.20282    ', 'http://arxiv.org/abs/1212.20282'),
    ('arxiv:arXiv:1212.20282', 'http://arxiv.org/abs/1212.20282'),
])
def test_arxiv_link(arxiv_id, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            ArXivLink().execute(arxiv_id)
        assert e.value.args == result.args
    else:
        assert rfc3987.parse(result)  # Extra URL validation
        assert ArXivLink().execute(arxiv_id)['IRI'] == result


@pytest.mark.parametrize('ark_id, result', [
    (None, TypeError('\'None\' is not of type str.')),
    ('', ValueError('\'\' is not a valid ARK Identifier.')),
    ('ark:/blah-blah-blah', ValueError('\'ark:/blah-blah-blah\' is not a valid ARK Identifier.')),
    ('something else', ValueError('\'something else\' is not a valid ARK Identifier.')),
    ('ark//1234/blah-blah-blah', ValueError('\'ark//1234/blah-blah-blah\' is not a valid ARK Identifier.')),
    ('ark:/1234', ValueError('\'ark:/1234\' is not a valid ARK Identifier.')),
    ('bark:/1234/blah-blah', ValueError('\'bark:/1234/blah-blah\' is not a valid ARK Identifier.')),
    ('ark:/1234a/blah-blah', ValueError('\'ark:/1234a/blah-blah\' is not a valid ARK Identifier.')),
    ('ark:/1234/blah-blah-blah', 'ark://1234/blah-blah-blah'),
    ('   ark:/1234/blah-blah-blah', 'ark://1234/blah-blah-blah'),
    ('ark:/1234/blah-blah-blah    ', 'ark://1234/blah-blah-blah'),
    ('http://namemappingauthority.org/ark:/1234/blah-blah-blah', 'ark://1234/blah-blah-blah'),
    ('ark:/383838/this/one/has/path', 'ark://383838/this/one/has/path'),
])
def test_ark_link(ark_id, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            ARKLink().execute(ark_id)
        assert e.value.args == result.args
    else:
        assert rfc3987.parse(result)  # Extra URL validation
        assert ARKLink().execute(ark_id)['IRI'] == result


@pytest.mark.parametrize('urn, result', [
    (None, TypeError('\'None\' is not of type str.')),
    ('', ValueError('\'\' is not a valid URN.')),
    ('something else', ValueError('\'something else\' is not a valid URN.')),
    ('oai:missing.path', ValueError('\'oai:missing.path\' is not a valid URN.')),
    ('oai::blank', ValueError('\'oai::blank\' is not a valid URN.')),
    ('oai://cos.io/fun', 'oai://cos.io/fun'),
    ('oai://cos.io/fun/times', 'oai://cos.io/fun/times'),
    ('oai://cos.io/fun/times/with/slashes', 'oai://cos.io/fun/times/with/slashes'),
    ('oai://cos.io/fun/ti mes', ValueError('\'oai://cos.io/fun/ti mes\' is not a valid URN.')),
    ('zenodo.com', ValueError('\'zenodo.com\' is not a valid URN.')),
    ('oai:invalid domain:this.is.stuff', ValueError('\'oai:invalid domain:this.is.stuff\' is not a valid URN.')),
    ('oai:domain.com:', ValueError('\'oai:domain.com:\' is not a valid URN.')),
    ('urn:missing.path', ValueError('\'urn:missing.path\' is not a valid URN.')),
    ('urn::blank', ValueError('\'urn::blank\' is not a valid URN.')),
    ('urn://cos.io/fun', 'urn://cos.io/fun'),
    ('urn:invalid domain:this.is.stuff', ValueError('\'urn:invalid domain:this.is.stuff\' is not a valid URN.')),
    ('urn:domain.com:', ValueError('\'urn:domain.com:\' is not a valid URN.')),
    ('oai:cos.io:this.is.stuff', 'oai://cos.io/this.is.stuff'),
    ('oai:subdomain.cos.io:this.is.stuff', 'oai://subdomain.cos.io/this.is.stuff'),
    ('    oai:cos.io:stuff', 'oai://cos.io/stuff'),
    ('    oai:cos.io:stuff  ', 'oai://cos.io/stuff'),
    ('oai:cos.io:long:list:of:things', 'oai://cos.io/long:list:of:things'),
    ('urn:share:this.is.stuff', 'urn://share/this.is.stuff'),
    ('    urn:share:stuff', 'urn://share/stuff'),
    ('    urn:share:stuff  ', 'urn://share/stuff'),
    ('urn:share:long:list:of/things', 'urn://share/long:list:of/things'),
])
def test_urn_link(urn, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            URNLink().execute(urn)
        assert e.value.args == result.args
    else:
        assert rfc3987.parse(result)  # Extra URL validation
        assert URNLink().execute(urn)['IRI'] == result


@pytest.mark.parametrize('uri, result', [
    ('info:eu-repo/grantAgreement/EC/FP7/280632/', 'info://eu-repo/grantAgreement/EC/FP7/280632/'),
    ('info:eu-repo/semantics/objectFile', 'info://eu-repo/semantics/objectFile'),
    ('      info:eu-repo/dai/nl/12345', 'info://eu-repo/dai/nl/12345'),
    ('\tinfo:eu-repo/dai/nl/12345\n', 'info://eu-repo/dai/nl/12345'),
    ('info:ddc/22/eng//004.678', 'info://ddc/22/eng//004.678'),
    ('info:lccn/2002022641', 'info://lccn/2002022641'),
    ('info:sici/0363-0277(19950315)120:5%3C%3E1.0.TX;2-V', 'info://sici/0363-0277(19950315)120:5%3C%3E1.0.TX;2-V'),
    ('fo:eu-repo/dai/nl/12345\n', ValueError("'fo:eu-repo/dai/nl/12345\n' is not a valid Info URI.")),
])
def test_info_link(uri, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            InfoURILink().execute(uri)
        assert e.value.args == result.args
    else:
        assert InfoURILink().execute(uri)['IRI'] == result


class TestIRILink:

    def _do_test(self, input, output, urn_fallback=False):
        if isinstance(output, Exception):
            with pytest.raises(type(output)) as e:
                IRILink().execute(input)
            assert e.value.args == output.args
        else:
            assert {k: v for k, v in IRILink(urn_fallback=urn_fallback).execute(input).items() if k in output} == output

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
        ('rééééééé@french-place.fr', {
            'scheme': 'mailto',
            'authority': 'french-place.fr',
            'IRI': 'mailto:rééééééé@french-place.fr',
        }),
        # This has a unicode hyphen "‐"
        ('JamesBond@chuchu\u2010train.fr', {
            'scheme': 'mailto',
            'authority': 'chuchu-train.fr',
            'IRI': 'mailto:JamesBond@chuchu-train.fr',
        }),

    ])
    def test_emails(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input, output', [
        ('http://api.elsevier.com/content/article/PII:B9780081005965212365?httpAccept=text/xml', {
            'scheme': 'http',
            'authority': 'api.elsevier.com',
            'IRI': 'http://api.elsevier.com/content/article/PII:B9780081005965212365?httpAccept=text/xml',
        }),
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
        ('www.GOOGLE.com:443/MixedCases', {
            'scheme': 'http',
            'authority': 'www.google.com',
            'IRI': 'http://www.google.com/MixedCases',
        }),
        ('https://google.com/#', {
            'scheme': 'http',
            'authority': 'google.com',
            'IRI': 'http://google.com/',
        }),
        ('https://google.com/#flooby', {
            'scheme': 'http',
            'authority': 'google.com',
            'IRI': 'http://google.com/#flooby',
        }),
        ('https://google.com/#fr/ag/ment', {
            'scheme': 'http',
            'authority': 'google.com',
            'IRI': 'http://google.com/#fr/ag/ment',
        }),
        ('https://google.com:666/', {
            'scheme': 'http',
            'authority': 'google.com:666',
            'IRI': 'http://google.com:666/',
        }),
        ('https://google.com:666/yay/path#yay/fragment', {
            'scheme': 'http',
            'authority': 'google.com:666',
            'IRI': 'http://google.com:666/yay/path#yay/fragment',
        }),
        ('http://www.scirp.org/journal/PaperDownload.aspx?DOI=10.4236/wjcd.2016.69035', {
            'scheme': 'http',
            'authority': 'www.scirp.org',
            'IRI': 'http://www.scirp.org/journal/PaperDownload.aspx?DOI=10.4236/wjcd.2016.69035',
        }),
        ('http://linkinghub.elsevier.com/retrieve/pii/s1053811912011895', {
            'scheme': 'http',
            'authority': 'linkinghub.elsevier.com',
            'IRI': 'http://linkinghub.elsevier.com/retrieve/pii/s1053811912011895',
        }),
        ('http://api.elsevier.com/content/article/PII:0168952590900517?httpAccept=text/xml', {
            'scheme': 'http',
            'authority': 'api.elsevier.com',
            'IRI': 'http://api.elsevier.com/content/article/PII:0168952590900517?httpAccept=text/xml',
        }),
        ('http://api.elsevier.com/content/article/PII:0168952590901608?httpAccept=text/xml', {
            'scheme': 'http',
            'authority': 'api.elsevier.com',
            'IRI': 'http://api.elsevier.com/content/article/PII:0168952590901608?httpAccept=text/xml',
        }),
        ('https://cn.dataone.org/cn/v2/resolve/http%3A%2F%2Fdx.doi.org%2F10.5061%2Fdryad.34s63%3Fformat%3Dd1rem%26ver%3D2016-11-03T17%3A08%3A53.816-04%3A00', {
            'scheme': 'http',
            'authority': 'cn.dataone.org',
            'IRI': 'http://cn.dataone.org/cn/v2/resolve/http%3A%2F%2Fdx.doi.org%2F10.5061%2Fdryad.34s63%3Fformat%3Dd1rem%26ver%3D2016-11-03T17%3A08%3A53.816-04%3A00'
        }),
        ('http://scitation.aip.org/deliver/fulltext/aip/journal/jcp/143/18/1.4935171.pdf?itemId=/content/aip/journal/jcp/143/18/10.1063/1.4935171&mimeType=pdf&containerItemId=content/aip/journal/jcp', {
            'scheme': 'http',
            'authority': 'scitation.aip.org',
            'IRI': 'http://scitation.aip.org/deliver/fulltext/aip/journal/jcp/143/18/1.4935171.pdf?itemId=/content/aip/journal/jcp/143/18/10.1063/1.4935171&mimeType=pdf&containerItemId=content/aip/journal/jcp',
        })
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
        ('arxiv:1212.20282', {
            'scheme': 'http',
            'authority': 'arxiv.org',
            'IRI': 'http://arxiv.org/abs/1212.20282'
        }),
        ('   arxiv:1212.20282', {
            'scheme': 'http',
            'authority': 'arxiv.org',
            'IRI': 'http://arxiv.org/abs/1212.20282'
        }),
        ('   arxiv:1212.20282    ', {
            'scheme': 'http',
            'authority': 'arxiv.org',
            'IRI': 'http://arxiv.org/abs/1212.20282'
        }),
        ('arxiv:arXiv:1212.20282', {
            'scheme': 'http',
            'authority': 'arxiv.org',
            'IRI': 'http://arxiv.org/abs/1212.20282'
        }),
    ])
    def test_arxiv_ids(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input, output', [
        ('ark:/1234/blah-blah-blah', {
            'scheme': 'ark',
            'authority': '1234',
            'path': '/blah-blah-blah'
        }),
        ('   ark:/1234/blah-blah-blah', {
            'scheme': 'ark',
            'authority': '1234',
            'path': '/blah-blah-blah'
        }),
        ('ark:/1234/blah-blah-blah    ', {
            'scheme': 'ark',
            'authority': '1234',
            'path': '/blah-blah-blah'
        }),
        ('http://namemappingauthority.org/ark:/1234/blah-blah-blah', {
            'scheme': 'ark',
            'authority': '1234',
            'path': '/blah-blah-blah'
        }),
        ('ark:/383838/this/one/has/path', {
            'scheme': 'ark',
            'authority': '383838',
            'path': '/this/one/has/path'
        }),
    ])
    def test_ark_ids(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input, output', [
        ('oai:cos.io:this.is.stuff', {
            'scheme': 'oai',
            'authority': 'cos.io',
            'IRI': 'oai://cos.io/this.is.stuff'
        }),
        ('oai:subdomain.cos.io:this.is.stuff', {
            'scheme': 'oai',
            'authority': 'subdomain.cos.io',
            'IRI': 'oai://subdomain.cos.io/this.is.stuff'
        }),
        ('    oai:cos.io:stuff', {
            'scheme': 'oai',
            'authority': 'cos.io',
            'IRI': 'oai://cos.io/stuff'
        }),
        ('    oai:cos.io:stuff  ', {
            'scheme': 'oai',
            'authority': 'cos.io',
            'IRI': 'oai://cos.io/stuff'
        }),
        ('oai:cos.io:long:list:of:things', {
            'scheme': 'oai',
            'authority': 'cos.io',
            'IRI': 'oai://cos.io/long:list:of:things'
        }),
        ('urn:cos.io:this.is.stuff', {
            'scheme': 'urn',
            'authority': 'cos.io',
            'IRI': 'urn://cos.io/this.is.stuff'
        }),
        ('    urn:cos.io:stuff', {
            'scheme': 'urn',
            'authority': 'cos.io',
            'IRI': 'urn://cos.io/stuff'
        }),
        ('    urn:cos.io:stuff  ', {
            'scheme': 'urn',
            'authority': 'cos.io',
            'IRI': 'urn://cos.io/stuff'
        }),
        ('urn:cos.io:long:list:of/things', {
            'scheme': 'urn',
            'authority': 'cos.io',
            'IRI': 'urn://cos.io/long:list:of/things'
        }),
    ])
    def test_urn_ids(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input, output', [
        ('info:eu-repo/grantAgreement/EC/FP7/280632/', {
            'scheme': 'info',
            'authority': 'eu-repo',
            'IRI': 'info://eu-repo/grantAgreement/EC/FP7/280632/',
        }),
        ('info:eu-repo/semantics/objectFile', {
            'scheme': 'info',
            'authority': 'eu-repo',
            'IRI': 'info://eu-repo/semantics/objectFile',
        }),
        ('      info:eu-repo/dai/nl/12345', {
            'scheme': 'info',
            'authority': 'eu-repo',
            'IRI': 'info://eu-repo/dai/nl/12345',
        }),
        ('\tinfo:eu-repo/dai/nl/12345\n', {
            'scheme': 'info',
            'authority': 'eu-repo',
            'IRI': 'info://eu-repo/dai/nl/12345',
        }),
        ('info:ddc/22/eng//004.678', {
            'scheme': 'info',
            'authority': 'ddc',
            'IRI': 'info://ddc/22/eng//004.678',
        }),
        ('info:lccn/2002022641', {
            'scheme': 'info',
            'authority': 'lccn',
            'IRI': 'info://lccn/2002022641'
        }),
        ('info:sici/0363-0277(19950315)120:5%3C%3E1.0.TX;2-V', {
            'scheme': 'info',
            'authority': 'sici',
            'IRI': 'info://sici/0363-0277(19950315)120:5%3C%3E1.0.TX;2-V'
        }),
    ])
    def test_info_uri(self, input, output):
        return self._do_test(input, output)

    @pytest.mark.parametrize('input, output', [
        (None, TypeError('\'None\' is not of type str.')),
        ('', ValueError('\'\' could not be identified as an Identifier.')),
        ('105517/ccdc.csd.cc1lj81f', ValueError('\'105517/ccdc.csd.cc1lj81f\' could not be identified as an Identifier.')),
        ('0.5517/ccdc.csd.cc1lj81f', ValueError('\'0.5517/ccdc.csd.cc1lj81f\' could not be identified as an Identifier.')),
        ('10.5517ccdc.csd.cc1lj81f', ValueError('\'10.5517ccdc.csd.cc1lj81f\' could not be identified as an Identifier.')),
        ('10.517ccdc.csd.cc1lj81f', ValueError('\'10.517ccdc.csd.cc1lj81f\' could not be identified as an Identifier.')),
        ('10.517/ccdc.csd.cc1lj81f', ValueError('\'10.517/ccdc.csd.cc1lj81f\' could not be identified as an Identifier.')),
        ('10.517ccdc.csd.c>c1lj81f', ValueError('\'10.517ccdc.csd.c>c1lj81f\' could not be identified as an Identifier.')),
        ('0000000248692412', ValueError('\'0000000248692412\' could not be identified as an Identifier.')),
        ('0000000000000000', ValueError('\'0000000000000000\' could not be identified as an Identifier.')),
        ('arXiv:1023..20382', ValueError('\'arXiv:1023..20382\' could not be identified as an Identifier.')),
        ('arXiv:10102.22322', ValueError('\'arXiv:10102.22322\' could not be identified as an Identifier.')),
        ('arXiv:2.2', ValueError('\'arXiv:2.2\' could not be identified as an Identifier.')),
        ('fo:eu-repo/dai/nl/12345\n', ValueError("'fo:eu-repo/dai/nl/12345\n' could not be identified as an Identifier.")),
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


class TestGuessAgentTypeLink:
    @pytest.mark.parametrize('name, result', [
        ('University of Whales', 'institution'),
        ('Thomas Jefferson', 'person'),
        ('The Thomas Jefferson thing', 'organization'),
        ('Center For Open Science', 'organization'),
        ('Science Council', 'organization'),
        ('Open Science Foundation', 'organization'),
        ('American Chemical Society', 'organization'),
        ('School for Clowns', 'institution'),
        ('Clown College', 'institution'),
        ('Clowning Institute', 'institution'),
        ('The Clown Institution', 'institution'),
        ('Clowns and Clown Accessories, Inc.', 'organization'),
        ('All of the clowns', 'organization'),
        ('Clown Group', 'organization'),
        ('CLWN', 'organization'),
        ('Mr. Clown', 'person'),
        ('Ronald McDonald', 'person'),
    ])
    def test_without_explicit_default(self, name, result):
        assert GuessAgentTypeLink().execute(name) == result

    @pytest.mark.parametrize('name, default, result', [
        ('University of Whales', 'organization', 'institution'),
        ('Thomas Jefferson', 'person', 'person'),
        ('Thomas Jefferson', 'organization', 'organization'),
        ('Thomas Jefferson', 'institution', 'institution'),
        ('The Thomas Jefferson thing', 'institution', 'organization'),
        ('Center For Open Science', 'person', 'organization'),
        ('Science Council', 'person', 'organization'),
        ('Open Science Foundation', 'person', 'organization'),
        ('American Chemical Society', 'person', 'organization'),
        ('School for Clowns', 'person', 'institution'),
        ('Clown College', 'person', 'institution'),
        ('Clowning Institute', 'person', 'institution'),
        ('The Clown Institution', 'person', 'institution'),
        ('Clowns and Clown Accessories, Inc.', 'person', 'organization'),
        ('All of the clowns', 'person', 'organization'),
        ('Clown Group', 'person', 'organization'),
        ('CLWN', 'person', 'organization'),
        ('Mr. Clown', 'organization', 'organization'),
        ('Ronald McDonald', 'person', 'person'),
        ('Ronald McDonald', 'organization', 'organization'),
        ('Ronald McDonald', 'institution', 'institution'),
    ])
    def test_with_default(self, name, default, result):
        assert GuessAgentTypeLink(default=default).execute(name) == result
