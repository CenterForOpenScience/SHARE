import pytest
import hashlib

from django.core import exceptions
from django.db.utils import IntegrityError

from share.models import RawData


@pytest.mark.django_db
class TestRawData:

    def test_doesnt_mangle_data(self, share_source):
        rd = RawData(source=share_source, data=b'This is just some data')
        rd.save()

        assert RawData.objects.first().data == 'This is just some data'

    def test_must_have_data(self, share_source):
        rd = RawData(source=share_source)

        with pytest.raises(exceptions.ValidationError) as e:
            rd.save()

        assert '"data" on {!r} can not be blank or empty'.format(rd) == e.value.args[0]

    def test_must_have_source(self):
        rd = RawData(data='SomeData')

        with pytest.raises(IntegrityError) as e:
            rd.save()

        assert 'null value in column "source_id" violates not-null constraint' in e.value.args[0]

    def test_store_data(self, share_source):
        rd = RawData.objects.store_data('myid', b'mydatums', share_source)

        assert rd.date_seen is not None
        assert rd.date_harvested is not None

        assert rd.data == b'mydatums'
        assert rd.source == share_source
        assert rd.provider_doc_id == 'myid'
        assert rd.sha256 == hashlib.sha256(b'mydatums').hexdigest()

    def test_store_data_dedups(self, share_source):
        rd1 = RawData.objects.store_data('myid', b'mydatums', share_source)
        rd2 = RawData.objects.store_data('myid', b'mydatums', share_source)

        assert rd1.pk == rd2.pk
        assert rd1.date_seen < rd2.date_seen
        assert rd1.date_harvested == rd2.date_harvested
