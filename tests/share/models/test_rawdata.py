import datetime
import pytest
import hashlib

from django.core import exceptions
from django.db.utils import IntegrityError

from share.models import RawDatum
from share.harvest.base import FetchResult


@pytest.mark.django_db
class TestRawDatum:

    def test_doesnt_mangle_data(self, suid):
        rd = RawDatum(suid=suid, datum='This is just some data')
        rd.save()

        assert RawDatum.objects.first().datum == 'This is just some data'

    def test_must_have_data(self, suid):
        rd = RawDatum(suid)

        with pytest.raises(exceptions.ValidationError) as e:
            rd.clean_fields()
            rd.save()

        assert 'This field cannot be blank.' == e.value.message_dict['datum'][0]

    def test_must_have_suid(self):
        rd = RawDatum(datum='SomeData')

        with pytest.raises(IntegrityError) as e:
            rd.save()

        assert 'null value in column "suid_id"' in e.value.args[0]

    def test_store_data(self, source_config):
        rd = RawDatum.objects.store_data(source_config, FetchResult('unique', 'mydatums'))

        assert rd.date_modified is not None
        assert rd.date_created is not None

        assert rd.datum == 'mydatums'
        assert rd.suid.identifier == 'unique'
        assert rd.suid.source_config == source_config
        assert rd.sha256 == hashlib.sha256(b'mydatums').hexdigest()

    def test_store_data_dedups_simple(self, source_config):
        rd1 = RawDatum.objects.store_data(source_config, FetchResult('unique', 'mydatums'))
        rd2 = RawDatum.objects.store_data(source_config, FetchResult('unique', 'mydatums'))

        assert rd1.pk == rd2.pk
        assert rd1.created is True
        assert rd2.created is False
        assert rd1.date_created == rd2.date_created
        assert rd1.date_modified < rd2.date_modified

    def test_store_data_dedups_complex(self, source_config):
        data = '{"providerUpdatedDateTime":"2016-08-25T11:37:40Z","uris":{"canonicalUri":"https://provider.domain/files/7d2792031","providerUris":["https://provider.domain/files/7d2792031"]},"contributors":[{"name":"Person1","email":"one@provider.domain"},{"name":"Person2","email":"two@provider.domain"},{"name":"Person3","email":"three@provider.domain"},{"name":"Person4","email":"dxm6@psu.edu"}],"title":"ReducingMorbiditiesinNeonatesUndergoingMRIScannig"}'
        rd1 = RawDatum.objects.store_data(source_config, FetchResult('unique', data))
        rd2 = RawDatum.objects.store_data(source_config, FetchResult('unique', data))

        assert rd1.pk == rd2.pk
        assert rd1.created is True
        assert rd2.created is False
        assert rd1.date_modified < rd2.date_modified
        assert rd1.date_created == rd2.date_created

    def test_is_expired(self):
        rd = RawDatum()
        assert rd.expiration_date is None
        assert not rd.is_expired
        _today = datetime.date.today()
        rd.expiration_date = datetime.date(_today.year - 1, _today.month, _today.day)
        assert rd.is_expired
        rd.expiration_date = datetime.date(_today.year, _today.month, _today.day)
        assert rd.is_expired
        rd.expiration_date = datetime.date(_today.year + 1, _today.month, _today.day)
        assert not rd.is_expired
