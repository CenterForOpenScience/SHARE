import pytest
import hashlib

from django.core import exceptions
from django.db.utils import IntegrityError

from share.models import RawData


@pytest.mark.django_db
class TestRawData:

    def test_doesnt_mangle_data(self, suid):
        rd = RawData(suid=suid, data=b'This is just some data')
        rd.save()

        assert RawData.objects.first().data == 'This is just some data'

    def test_must_have_data(self, suid):
        rd = RawData(suid=suid)

        with pytest.raises(exceptions.ValidationError) as e:
            rd.clean_fields()
            rd.save()

        assert 'This field cannot be blank.' == e.value.message_dict['data'][0]

    def test_must_have_suid(self):
        rd = RawData(data='SomeData')

        with pytest.raises(IntegrityError) as e:
            rd.save()

        assert 'null value in column "suid_id" violates not-null constraint' in e.value.args[0]

    def test_store_data(self, suid):
        rd = RawData.objects.store_data(b'mydatums', suid)

        assert rd.date_seen is not None
        assert rd.date_harvested is not None

        assert rd.data == b'mydatums'
        assert rd.suid == suid
        assert rd.sha256 == hashlib.sha256(b'mydatums').hexdigest()

    def test_store_data_dedups_simple(self, suid):
        rd1 = RawData.objects.store_data(b'mydatums', suid)
        rd2 = RawData.objects.store_data(b'mydatums', suid)

        assert rd1.pk == rd2.pk
        assert rd1.date_seen < rd2.date_seen
        assert rd1.date_harvested == rd2.date_harvested

    def test_store_data_dedups_complex(self, suid):
        data = b'{"providerUpdatedDateTime":"2016-08-25T11:37:40Z","uris":{"canonicalUri":"https://provider.domain/files/7d2792031","providerUris":["https://provider.domain/files/7d2792031"]},"contributors":[{"name":"Person1","email":"one@provider.domain"},{"name":"Person2","email":"two@provider.domain"},{"name":"Person3","email":"three@provider.domain"},{"name":"Person4","email":"dxm6@psu.edu"}],"title":"ReducingMorbiditiesinNeonatesUndergoingMRIScannig"}'
        rd1 = RawData.objects.store_data(data, suid)
        rd2 = RawData.objects.store_data(data, suid)

        assert rd1.pk == rd2.pk
        assert rd1.date_seen < rd2.date_seen
        assert rd1.date_harvested == rd2.date_harvested
