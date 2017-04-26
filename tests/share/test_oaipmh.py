import math
import pendulum
import pytest
import random
from lxml import etree

from django.test.client import Client

from share import models
from share.oaipmh.util import format_datetime
from share.util import IDObfuscator

from tests.share.models import factories


NAMESPACES = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'ns0': 'http://www.openarchives.org/OAI/2.0/',
    'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
}


@pytest.fixture
def oai_works():
    return [factories.PreprintFactory() for i in range(17)]


def oai_request(data, post, errors=False):
    client = Client()
    if post:
        response = client.post('/oai-pmh/', data)
    else:
        response = client.get('/oai-pmh/', data)
    assert response.status_code == 200
    parsed = etree.fromstring(response.content, parser=etree.XMLParser(recover=True))
    actual_errors = parsed.xpath('//ns0:error', namespaces=NAMESPACES)
    if errors:
        assert actual_errors
        return actual_errors
    assert not actual_errors
    return parsed


@pytest.mark.django_db
@pytest.mark.parametrize('post', [True, False])
class TestOAIVerbs:

    def test_identify(self, post):
        parsed = oai_request({'verb': 'Identify'}, post)
        assert parsed.xpath('//ns0:Identify/ns0:repositoryName', namespaces=NAMESPACES)[0].text == 'SHARE'

    def test_list_sets(self, post):
        parsed = oai_request({'verb': 'ListSets'}, post)
        assert len(parsed.xpath('//ns0:ListSets/ns0:set', namespaces=NAMESPACES)) > 100

    def test_list_formats(self, post):
        parsed = oai_request({'verb': 'ListMetadataFormats'}, post)
        prefixes = parsed.xpath('//ns0:ListMetadataFormats/ns0:metadataFormat/ns0:metadataPrefix', namespaces=NAMESPACES)
        assert len(prefixes) == 1
        assert prefixes[0].text == 'oai_dc'

    def test_list_identifiers(self, post, all_about_anteaters):
        parsed = oai_request({'verb': 'ListIdentifiers', 'metadataPrefix': 'oai_dc'}, post)
        identifiers = parsed.xpath('//ns0:ListIdentifiers/ns0:header/ns0:identifier', namespaces=NAMESPACES)
        assert len(identifiers) == 1
        assert identifiers[0].text == 'oai:share.osf.io:{}'.format(IDObfuscator.encode(all_about_anteaters))

    def test_list_records(self, post, all_about_anteaters):
        parsed = oai_request({'verb': 'ListRecords', 'metadataPrefix': 'oai_dc'}, post)
        records = parsed.xpath('//ns0:ListRecords/ns0:record', namespaces=NAMESPACES)
        assert len(records) == 1
        assert all_about_anteaters.title == records[0].xpath('ns0:metadata/oai_dc:dc/dc:title', namespaces=NAMESPACES)[0].text
        ant_id = 'oai:share.osf.io:{}'.format(IDObfuscator.encode(all_about_anteaters))
        assert ant_id == records[0].xpath('ns0:header/ns0:identifier', namespaces=NAMESPACES)[0].text

    def test_get_record(self, post, all_about_anteaters):
        ant_id = 'oai:share.osf.io:{}'.format(IDObfuscator.encode(all_about_anteaters))
        parsed = oai_request({'verb': 'GetRecord', 'metadataPrefix': 'oai_dc', 'identifier': ant_id}, post)
        records = parsed.xpath('//ns0:GetRecord/ns0:record', namespaces=NAMESPACES)
        assert len(records) == 1
        assert all_about_anteaters.title == records[0].xpath('ns0:metadata/oai_dc:dc/dc:title', namespaces=NAMESPACES)[0].text
        assert ant_id == records[0].xpath('ns0:header/ns0:identifier', namespaces=NAMESPACES)[0].text

    @pytest.mark.parametrize('verb, params, errors', [
        ('GetRecord', {}, ['badArgument']),
        ('GetRecord', {'something': '{id}'}, ['badArgument']),
        ('GetRecord', {'identifier': '{id}'}, ['badArgument']),
        ('GetRecord', {'identifier': 'bad', 'metadataPrefix': 'oai_dc'}, ['idDoesNotExist']),
        ('GetRecord', {'identifier': '{id}', 'metadataPrefix': 'bad'}, ['cannotDisseminateFormat']),
        ('Identify', {'metadataPrefix': 'oai_dc'}, ['badArgument']),
        ('ListIdentifiers', {}, ['badArgument']),
        ('ListIdentifiers', {'something': '{id}'}, ['badArgument']),
        ('ListIdentifiers', {'metadataPrefix': 'bad'}, ['cannotDisseminateFormat']),
        ('ListIdentifiers', {'set': 'not_a_set', 'metadataPrefix': 'oai_dc'}, ['noRecordsMatch']),
        ('ListIdentifiers', {'resumptionToken': 'token', 'metadataPrefix': 'oai_dc'}, ['badArgument']),
        ('ListIdentifiers', {'resumptionToken': 'token'}, ['badResumptionToken']),
        ('ListRecords', {}, ['badArgument']),
        ('ListRecords', {'something': '{id}'}, ['badArgument']),
        ('ListRecords', {'metadataPrefix': 'bad'}, ['cannotDisseminateFormat']),
        ('ListRecords', {'set': 'not_a_set', 'metadataPrefix': 'oai_dc'}, ['noRecordsMatch']),
        ('ListRecords', {'resumptionToken': 'token', 'metadataPrefix': 'oai_dc'}, ['badArgument']),
        ('ListRecords', {'resumptionToken': 'token'}, ['badResumptionToken']),
        ('ListMetadataFormats', {'metadataPrefix': 'oai_dc'}, ['badArgument']),
        ('ListMetadataFormats', {'identifier': 'bad_identifier'}, ['idDoesNotExist']),
        ('ListSets', {'something': 'oai_dc'}, ['badArgument']),
        ('ListSets', {'resumptionToken': 'bad_token'}, ['badResumptionToken']),
    ])
    def test_oai_errors(self, verb, params, errors, post, all_about_anteaters):
        ant_id = IDObfuscator.encode(all_about_anteaters)
        data = {'verb': verb, **{k: v.format(id=ant_id) for k, v in params.items()}}
        actual_errors = oai_request(data, post, errors=True)
        for error_code in errors:
            assert any(e.attrib.get('code') == error_code for e in actual_errors)


@pytest.mark.django_db
@pytest.mark.parametrize('post', [True, False])
@pytest.mark.parametrize('verb', ['ListRecords', 'ListIdentifiers'])
@pytest.mark.parametrize('page_size', [5, 10, 100])
class TestOAILists:

    def test_full_list(self, oai_works, post, verb, page_size, monkeypatch):
        monkeypatch.setattr('share.oaipmh.repository.OAIRepository.PAGE_SIZE', page_size)
        self._assert_full_list(verb, {}, post, len(oai_works), page_size)

    @pytest.mark.parametrize('from_date, to_date, expected_count', [
        (pendulum.now().subtract(days=1), None, 17),
        (None, pendulum.now().subtract(days=1), 0),
        (pendulum.now().add(days=1), None, 0),
        (None, pendulum.now().add(days=1), 17),
        (pendulum.now().subtract(days=1), pendulum.now().add(days=1), 17),
    ])
    def test_filter_date(self, oai_works, post, verb, page_size, monkeypatch, from_date, to_date, expected_count):
        monkeypatch.setattr('share.oaipmh.repository.OAIRepository.PAGE_SIZE', page_size)
        params = {}
        if from_date:
            params['from'] = format_datetime(from_date)
        if to_date:
            params['until'] = format_datetime(to_date)
        self._assert_full_list(verb, params, post, expected_count, page_size)

    @pytest.mark.parametrize('expected_count', range(0, 17, 6))
    def test_filter_set(self, oai_works, post, verb, page_size, monkeypatch, expected_count):
        monkeypatch.setattr('share.oaipmh.repository.OAIRepository.PAGE_SIZE', page_size)
        source = models.Source.objects.select_related('user').first()
        for work in random.sample(oai_works, expected_count):
            work.sources.add(source.user)

        self._assert_full_list(verb, {'set': source.name}, post, expected_count, page_size)

    def _assert_full_list(self, verb, params, post, expected_count, page_size):
        if not expected_count:
            errors = oai_request({'verb': verb, 'metadataPrefix': 'oai_dc', **params}, post, errors=True)
            assert len(errors) == 1
            assert errors[0].attrib.get('code') == 'noRecordsMatch'
            return

        datestamps = []
        pages = 0
        token = None
        while True:
            if token:
                parsed = oai_request({'verb': verb, 'resumptionToken': token}, post)
            else:
                parsed = oai_request({'verb': verb, 'metadataPrefix': 'oai_dc', **params}, post)
            page = parsed.xpath('//ns0:header/ns0:datestamp', namespaces=NAMESPACES)
            datestamps.extend(page)
            pages += 1
            token = parsed.xpath('//ns0:resumptionToken', namespaces=NAMESPACES)
            assert len(token) == 1
            token = token[0].text
            if token:
                assert len(page) == page_size
            else:
                assert len(page) <= page_size
                break

        assert len(datestamps) == expected_count
        assert pages == math.ceil(expected_count / page_size)
        for i in range(len(datestamps) - 1):
            assert datestamps[i].text >= datestamps[i + 1].text
