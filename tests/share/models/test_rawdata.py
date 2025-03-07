import datetime
import pytest
import hashlib

from django.core import exceptions
from django.db.utils import IntegrityError

from share.models import RawDatum


def get_now():
    return datetime.datetime.now(tz=datetime.timezone.utc)


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

    def test_store_data_by_suid(self, suid):
        _now = get_now()
        rd = RawDatum.objects.store_datum_for_suid(
            suid=suid,
            datum='mydatums',
            mediatype='text/plain',
            datestamp=_now,
        )

        assert rd.date_modified is not None
        assert rd.date_created is not None

        assert rd.datum == 'mydatums'
        assert rd.datestamp == _now
        assert rd.suid_id == suid.id
        assert rd.sha256 == hashlib.sha256(b'mydatums').hexdigest()

    def test_store_data_dedups_simple(self, suid):
        rd1 = RawDatum.objects.store_datum_for_suid(
            suid=suid,
            datum='mydatums',
            mediatype='text/plain',
            datestamp=get_now(),
        )
        rd2 = RawDatum.objects.store_datum_for_suid(
            suid=suid,
            datum='mydatums',
            mediatype='text/plain',
            datestamp=get_now(),
        )
        rd3 = RawDatum.objects.store_datum_for_suid(
            suid=suid,
            datum='mydatums',
            mediatype='text/plain',
            datestamp=get_now(),
        )

        assert rd1.pk == rd2.pk == rd3.pk
        assert rd1.sha256 == rd2.sha256 == rd3.sha256
        assert rd1.datestamp < rd2.datestamp < rd3.datestamp < get_now()
        assert rd1.date_created == rd2.date_created == rd3.date_created
        assert rd1.date_modified < rd2.date_modified < rd3.date_modified

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
