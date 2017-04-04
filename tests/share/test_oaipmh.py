import pytest
from lxml import etree

from django.test.client import Client

from share.util import IDObfuscator


@pytest.mark.django_db
@pytest.mark.parametrize('post', [True, False])
class TestOAIPMH:
    namespaces = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ns0': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
    }

    def test_identify(self, post):
        parsed = self._request({'verb': 'Identify'}, post)
        assert parsed.xpath('//ns0:Identify/ns0:repositoryName', namespaces=self.namespaces)[0].text == 'SHARE'

    def test_list_sets(self, post):
        parsed = self._request({'verb': 'ListSets'}, post)
        assert len(parsed.xpath('//ns0:ListSets/ns0:set', namespaces=self.namespaces)) > 100

    def test_list_formats(self, post):
        parsed = self._request({'verb': 'ListMetadataFormats'}, post)
        prefixes = parsed.xpath('//ns0:ListMetadataFormats/ns0:metadataFormat/ns0:metadataPrefix', namespaces=self.namespaces)
        assert len(prefixes) == 1
        assert prefixes[0].text == 'oai_dc'

    def test_list_identifiers(self, post, all_about_anteaters):
        parsed = self._request({'verb': 'ListIdentifiers', 'metadataPrefix': 'oai_dc'}, post)
        identifiers = parsed.xpath('//ns0:ListIdentifiers/ns0:header/ns0:identifier', namespaces=self.namespaces)
        assert len(identifiers) == 1
        assert identifiers[0].text == 'oai:share.osf.io:{}'.format(IDObfuscator.encode(all_about_anteaters))

    def test_list_records(self, post, all_about_anteaters):
        parsed = self._request({'verb': 'ListRecords', 'metadataPrefix': 'oai_dc'}, post)
        records = parsed.xpath('//ns0:ListRecords/ns0:record', namespaces=self.namespaces)
        assert len(records) == 1
        assert all_about_anteaters.title == records[0].xpath('ns0:metadata/oai_dc:dc/dc:title', namespaces=self.namespaces)[0].text
        ant_id = 'oai:share.osf.io:{}'.format(IDObfuscator.encode(all_about_anteaters))
        assert ant_id == records[0].xpath('ns0:header/ns0:identifier', namespaces=self.namespaces)[0].text

    def test_get_record(self, post, all_about_anteaters):
        ant_id = 'oai:share.osf.io:{}'.format(IDObfuscator.encode(all_about_anteaters))
        parsed = self._request({'verb': 'GetRecord', 'metadataPrefix': 'oai_dc', 'identifier': ant_id}, post)
        records = parsed.xpath('//ns0:GetRecord/ns0:record', namespaces=self.namespaces)
        assert len(records) == 1
        assert all_about_anteaters.title == records[0].xpath('ns0:metadata/oai_dc:dc/dc:title', namespaces=self.namespaces)[0].text
        assert ant_id == records[0].xpath('ns0:header/ns0:identifier', namespaces=self.namespaces)[0].text

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
        actual_errors = self._request(data, post, errors=True)
        for error_code in errors:
            assert any(e.attrib.get('code') == error_code for e in actual_errors)

    def _request(self, data, post, errors=False):
        client = Client()
        if post:
            response = client.post('/oai-pmh/', data)
        else:
            response = client.get('/oai-pmh/', data)
        assert response.status_code == 200
        parsed = etree.fromstring(response.content, parser=etree.XMLParser(recover=True))
        actual_errors = parsed.xpath('//ns0:error', namespaces=self.namespaces)
        if errors:
            assert actual_errors
            return actual_errors
        assert not actual_errors
        return parsed
