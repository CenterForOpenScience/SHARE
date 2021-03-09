import math
import pendulum
import pytest
import random
from lxml import etree

from django.test.client import Client

from share.models import SourceUniqueIdentifier, FormattedMetadataRecord
from share.oaipmh.util import format_datetime
from share.util import IDObfuscator

from tests.factories import FormattedMetadataRecordFactory, SourceFactory


NAMESPACES = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'ns0': 'http://www.openarchives.org/OAI/2.0/',
    'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
}


def oai_request(data, pls_post, expect_errors=False):
    client = Client()
    data = {
        **data,
        'pls_trove': True,
    }
    if pls_post:
        response = client.post('/oai-pmh/', data)
    else:
        response = client.get('/oai-pmh/', data)
    assert response.status_code == 200
    parsed = etree.fromstring(response.content, parser=etree.XMLParser(recover=True))
    actual_errors = parsed.xpath('//ns0:error', namespaces=NAMESPACES)
    if expect_errors:
        assert actual_errors
        return actual_errors
    assert not actual_errors, [etree.tostring(e, encoding='unicode') for e in actual_errors]
    return parsed


@pytest.mark.django_db
@pytest.mark.parametrize('post', [True, False])
class TestOAIVerbs:
    @pytest.fixture
    def oai_record(self):
        return FormattedMetadataRecordFactory(
            record_format='oai_dc',
            formatted_metadata='<foo></foo>',
        )

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

    def test_list_identifiers(self, post, oai_record):
        parsed = oai_request({'verb': 'ListIdentifiers', 'metadataPrefix': 'oai_dc'}, post)
        identifiers = parsed.xpath('//ns0:ListIdentifiers/ns0:header/ns0:identifier', namespaces=NAMESPACES)
        assert len(identifiers) == 1
        assert identifiers[0].text == 'oai:share.osf.io:{}'.format(IDObfuscator.encode(oai_record.suid))

    def test_list_records(self, post, oai_record, django_assert_num_queries):
        with django_assert_num_queries(1):
            parsed = oai_request({'verb': 'ListRecords', 'metadataPrefix': 'oai_dc'}, post)
        records = parsed.xpath('//ns0:ListRecords/ns0:record', namespaces=NAMESPACES)
        assert len(records) == 1
        assert len(records[0].xpath('ns0:metadata/ns0:foo', namespaces=NAMESPACES)) == 1
        record_id = 'oai:share.osf.io:{}'.format(IDObfuscator.encode(oai_record.suid))
        assert record_id == records[0].xpath('ns0:header/ns0:identifier', namespaces=NAMESPACES)[0].text

    def test_get_record(self, post, oai_record):
        ant_id = 'oai:share.osf.io:{}'.format(IDObfuscator.encode(oai_record.suid))
        parsed = oai_request({'verb': 'GetRecord', 'metadataPrefix': 'oai_dc', 'identifier': ant_id}, post)
        records = parsed.xpath('//ns0:GetRecord/ns0:record', namespaces=NAMESPACES)
        assert len(records) == 1
        assert len(records[0].xpath('ns0:metadata/ns0:foo', namespaces=NAMESPACES)) == 1
        assert ant_id == records[0].xpath('ns0:header/ns0:identifier', namespaces=NAMESPACES)[0].text

    @pytest.mark.parametrize('verb, params, errors', [
        ('GetRecord', {}, ['badArgument']),
        ('GetRecord', {'something': '{id}'}, ['badArgument']),
        ('GetRecord', {'identifier': '{id}'}, ['badArgument']),
        ('GetRecord', {'identifier': 'oai:share.osf.io:DEADB-EEE-EEF'}, ['badArgument']),
        ('GetRecord', {'identifier': 'bad', 'metadataPrefix': 'oai_dc'}, ['idDoesNotExist']),
        ('GetRecord', {'identifier': '{id}', 'metadataPrefix': 'bad'}, ['cannotDisseminateFormat']),
        ('GetRecord', {'identifier': 'oai:share.osf.io:DEADB-EEE-EEF', 'metadataPrefix': 'oai_dc'}, ['idDoesNotExist']),
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
        ('ListMetadataFormats', {'identifier': 'oai:share.osf.io:DEADB-EEE-EEF'}, ['idDoesNotExist']),
        ('ListSets', {'something': 'oai_dc'}, ['badArgument']),
        ('ListSets', {'resumptionToken': 'bad_token'}, ['badResumptionToken']),
    ])
    def test_oai_errors(self, verb, params, errors, post, oai_record):
        record_id = IDObfuscator.encode(oai_record.suid)
        data = {'verb': verb, **{k: v.format(id=record_id) for k, v in params.items()}}
        actual_errors = oai_request(data, post, expect_errors=True)
        actual_error_codes = {e.attrib.get('code') for e in actual_errors}
        assert actual_error_codes == set(errors)

    def test_subtly_wrong_identifiers(self, post, oai_record):
        # obfuscated id points to the correct table, but a non-existent row
        self._assert_bad_identifier(post, IDObfuscator.encode_id(
            self._get_nonexistent_id(SourceUniqueIdentifier),
            SourceUniqueIdentifier,
        ))

        # obfuscated id points to the wrong table, but an existing row
        self._assert_bad_identifier(post, IDObfuscator.encode(oai_record))

        # obfuscated id points to the wrong table, and a non-existent row
        self._assert_bad_identifier(post, IDObfuscator.encode_id(
            self._get_nonexistent_id(FormattedMetadataRecord),
            FormattedMetadataRecord,
        ))

    def _get_nonexistent_id(self, model_class):
        last_id = model_class.objects.order_by('-id').values_list('id', flat=True).first()
        nonexistent_id = last_id + 1
        assert not model_class.objects.filter(id=nonexistent_id).exists()
        return nonexistent_id

    def _assert_bad_identifier(self, post, bad_identifier):
        full_bad_identifier = f'oai:share.osf.io:{bad_identifier}'
        request_param_sets = [{
            'verb': 'GetRecord',
            'metadataPrefix': 'oai_dc',
            'identifier': full_bad_identifier,
        }, {
            'verb': 'ListMetadataFormats',
            'identifier': full_bad_identifier,
        }]
        for params in request_param_sets:
            actual_errors = oai_request(params, post, expect_errors=True)
            actual_error_codes = {
                e.attrib.get('code')
                for e in actual_errors
            }
            assert actual_error_codes == {'idDoesNotExist'}


@pytest.mark.django_db
class TestOAILists:
    @pytest.fixture
    def oai_records(self):
        return [
            FormattedMetadataRecordFactory(
                record_format='oai_dc',
                formatted_metadata='<foo></foo>',
            )
            for i in range(17)
        ]

    # all combined into one massive test to avoid rebuilding the oai_records fixture
    # repeatedly -- pytest-django can't handle a db-using fixture with scope='class'
    def test_lists(self, oai_records, monkeypatch):
        test_params_list = [
            (pls_post, verb, page_size)
            for pls_post in [True, False]
            for verb in ['ListRecords', 'ListIdentifiers']
            for page_size in [5, 10, 100]
        ]
        for pls_post, verb, page_size in test_params_list:
            monkeypatch.setattr('share.oaipmh.fmr_repository.OaiPmhRepository.PAGE_SIZE', page_size)
            self._assert_full_list(verb, {}, pls_post, len(oai_records), page_size)
            self._test_filter_date(oai_records, pls_post, verb, page_size)
            self._test_filter_set(oai_records, pls_post, verb, page_size)

    def _test_filter_date(self, oai_records, pls_post, verb, page_size):
        for from_date, to_date, expected_count in [
            (pendulum.now().subtract(days=1), None, 17),
            (None, pendulum.now().subtract(days=1), 0),
            (pendulum.now().add(days=1), None, 0),
            (None, pendulum.now().add(days=1), 17),
            (pendulum.now().subtract(days=1), pendulum.now().add(days=1), 17),
        ]:
            params = {}
            if from_date:
                params['from'] = format_datetime(from_date)
            if to_date:
                params['until'] = format_datetime(to_date)
            self._assert_full_list(verb, params, pls_post, expected_count, page_size)

    def _test_filter_set(self, oai_records, pls_post, verb, page_size):
        source = SourceFactory()

        # empty list
        self._assert_full_list(verb, {'set': source.name}, pls_post, 0, page_size)

        for record in random.sample(oai_records, 7):
            source_config = record.suid.source_config
            source_config.source = source
            source_config.save()

        self._assert_full_list(verb, {'set': source.name}, pls_post, 7, page_size)

    def _assert_full_list(self, verb, params, post, expected_count, page_size):
        if not expected_count:
            errors = oai_request({'verb': verb, 'metadataPrefix': 'oai_dc', **params}, post, expect_errors=True)
            assert len(errors) == 1
            assert errors[0].attrib.get('code') == 'noRecordsMatch'
            return

        pages = 0
        count = 0
        token = None
        while True:
            if token:
                parsed = oai_request({'verb': verb, 'resumptionToken': token}, post)
            else:
                parsed = oai_request({'verb': verb, 'metadataPrefix': 'oai_dc', **params}, post)
            page = parsed.xpath('//ns0:header/ns0:identifier', namespaces=NAMESPACES)
            pages += 1
            count += len(page)
            token = parsed.xpath('//ns0:resumptionToken', namespaces=NAMESPACES)
            assert len(token) == 1
            token = token[0].text
            if token:
                assert len(page) == page_size
            else:
                assert len(page) <= page_size
                break

        assert count == expected_count
        assert pages == math.ceil(expected_count / page_size)
