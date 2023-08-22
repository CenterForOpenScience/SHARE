import math
import random
import uuid

from django.test.client import Client
from lxml import etree
import pendulum
import pytest

from share import models as share_db
from share.oaipmh.util import format_datetime
from trove import models as trove_db
from trove.vocab.namespaces import OAI_DC

from tests import factories


NAMESPACES = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'ns0': 'http://www.openarchives.org/OAI/2.0/',
    'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
}


def oai_request(data, request_method, expect_errors=False):
    client = Client()
    if request_method == 'POST':
        response = client.post('/oai-pmh/', data)
    elif request_method == 'GET':
        response = client.get('/oai-pmh/', data)
    else:
        raise NotImplementedError
    assert response.status_code == 200
    parsed = etree.fromstring(response.content, parser=etree.XMLParser(recover=True))
    actual_errors = parsed.xpath('//ns0:error', namespaces=NAMESPACES)
    if expect_errors:
        assert actual_errors
        return actual_errors
    assert not actual_errors, [etree.tostring(e, encoding='unicode') for e in actual_errors]
    return parsed


@pytest.mark.usefixtures('nested_django_db')
class TestOAIVerbs:
    @pytest.fixture(scope='class')
    def oai_indexcard(self, class_scoped_django_db):
        _latest_indexcard_rdf = factories.LatestIndexcardRdfFactory()
        return factories.DerivedIndexcardFactory(
            upriver_indexcard=_latest_indexcard_rdf.indexcard,
            deriver_identifier=trove_db.ResourceIdentifier.objects.get_or_create_for_iri(str(OAI_DC)),
            derived_text='<foo></foo>',
        )

    @pytest.fixture(params=['POST', 'GET'])
    def request_method(self, request):
        return request.param

    def test_identify(self, request_method):
        parsed = oai_request({'verb': 'Identify'}, request_method)
        assert parsed.xpath('//ns0:Identify/ns0:repositoryName', namespaces=NAMESPACES)[0].text == 'Share/trove'

    def test_list_sets(self, request_method):
        parsed = oai_request({'verb': 'ListSets'}, request_method)
        _num_sets = len(parsed.xpath('//ns0:ListSets/ns0:set', namespaces=NAMESPACES))
        assert _num_sets == share_db.Source.objects.all().count()

    def test_list_formats(self, request_method):
        parsed = oai_request({'verb': 'ListMetadataFormats'}, request_method)
        prefixes = parsed.xpath('//ns0:ListMetadataFormats/ns0:metadataFormat/ns0:metadataPrefix', namespaces=NAMESPACES)
        assert len(prefixes) == 1
        assert prefixes[0].text == 'oai_dc'

    def test_list_identifiers(self, request_method, oai_indexcard):
        parsed = oai_request({'verb': 'ListIdentifiers', 'metadataPrefix': 'oai_dc'}, request_method)
        identifiers = parsed.xpath('//ns0:ListIdentifiers/ns0:header/ns0:identifier', namespaces=NAMESPACES)
        assert len(identifiers) == 1
        assert identifiers[0].text == 'oai:share.osf.io:{}'.format(oai_indexcard.upriver_indexcard.uuid)

    def test_list_records(self, request_method, oai_indexcard, django_assert_num_queries):
        with django_assert_num_queries(1):
            parsed = oai_request({'verb': 'ListRecords', 'metadataPrefix': 'oai_dc'}, request_method)
        records = parsed.xpath('//ns0:ListRecords/ns0:record', namespaces=NAMESPACES)
        assert len(records) == 1
        assert len(records[0].xpath('ns0:metadata/ns0:foo', namespaces=NAMESPACES)) == 1
        record_id = 'oai:share.osf.io:{}'.format(oai_indexcard.upriver_indexcard.uuid)
        assert record_id == records[0].xpath('ns0:header/ns0:identifier', namespaces=NAMESPACES)[0].text

    def test_get_record(self, request_method, oai_indexcard):
        ant_id = 'oai:share.osf.io:{}'.format(oai_indexcard.upriver_indexcard.uuid)
        parsed = oai_request({'verb': 'GetRecord', 'metadataPrefix': 'oai_dc', 'identifier': ant_id}, request_method)
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
    def test_oai_errors(self, verb, params, errors, request_method, oai_indexcard):
        record_id = oai_indexcard.upriver_indexcard.uuid
        data = {'verb': verb, **{k: v.format(id=record_id) for k, v in params.items()}}
        actual_errors = oai_request(data, request_method, expect_errors=True)
        actual_error_codes = {e.attrib.get('code') for e in actual_errors}
        assert actual_error_codes == set(errors)

    def test_subtly_wrong_identifiers(self, request_method, oai_indexcard):
        # unknown uuid
        self._assert_bad_identifier(request_method, str(uuid.uuid4()))
        # not a uuid
        self._assert_bad_identifier(request_method, 'DEADB-EEE-EEF')

    def _get_nonexistent_id(self, model_class):
        last_id = model_class.objects.order_by('-id').values_list('id', flat=True).first()
        nonexistent_id = last_id + 1
        assert not model_class.objects.filter(id=nonexistent_id).exists()
        return nonexistent_id

    def _assert_bad_identifier(self, request_method, bad_identifier):
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
            actual_errors = oai_request(params, request_method, expect_errors=True)
            actual_error_codes = {
                e.attrib.get('code')
                for e in actual_errors
            }
            assert actual_error_codes == {'idDoesNotExist'}


@pytest.mark.usefixtures('nested_django_db')
class TestOAILists:
    @pytest.fixture(scope='class')
    def oai_indexcards(self, class_scoped_django_db):
        _deriver_identifier = (
            trove_db.ResourceIdentifier.objects
            .get_or_create_for_iri(str(OAI_DC))
        )
        _latest_rdfs = [
            factories.LatestIndexcardRdfFactory()
            for i in range(17)
        ]
        return [
            factories.DerivedIndexcardFactory(
                upriver_indexcard=_latest_rdf.indexcard,
                deriver_identifier=_deriver_identifier,
                derived_text='<foo></foo>',
            )
            for _latest_rdf in _latest_rdfs
        ]

    def test_lists(self, oai_indexcards, monkeypatch):
        test_params_list = [
            (request_method, verb, page_size)
            for request_method in ['GET', 'POST']
            for verb in ['ListRecords', 'ListIdentifiers']
            for page_size in [7, 13, 101]
        ]
        for request_method, verb, page_size in test_params_list:
            monkeypatch.setattr('share.oaipmh.indexcard_repository.OaiPmhRepository.PAGE_SIZE', page_size)
            self._assert_full_list(verb, {}, request_method, len(oai_indexcards), page_size)
            self._test_filter_date(oai_indexcards, request_method, verb, page_size)
            self._test_filter_set(oai_indexcards, request_method, verb, page_size)

    def _test_filter_date(self, oai_indexcards, request_method, verb, page_size):
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
            self._assert_full_list(verb, params, request_method, expected_count, page_size)

    def _test_filter_set(self, oai_indexcards, request_method, verb, page_size):
        source = factories.SourceFactory()

        # empty list
        self._assert_full_list(verb, {'set': source.name}, request_method, 0, page_size)

        for _oai_indexcard in random.sample(oai_indexcards, 7):
            source_config = _oai_indexcard.upriver_indexcard.source_record_suid.source_config
            source_config.source = source
            source_config.save()

        self._assert_full_list(verb, {'set': source.name}, request_method, 7, page_size)

    def _assert_full_list(self, verb, params, request_method, expected_count, page_size):
        if not expected_count:
            errors = oai_request({'verb': verb, 'metadataPrefix': 'oai_dc', **params}, request_method, expect_errors=True)
            assert len(errors) == 1
            assert errors[0].attrib.get('code') == 'noRecordsMatch'
            return

        pages = 0
        count = 0
        token = None
        while True:
            if token:
                parsed = oai_request({'verb': verb, 'resumptionToken': token}, request_method)
            else:
                parsed = oai_request({'verb': verb, 'metadataPrefix': 'oai_dc', **params}, request_method)
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
