import pytest

from django.core import exceptions
from django.db.utils import IntegrityError

from share.models import RawData


@pytest.mark.django_db
def test_doesnt_mangle_data(share_source):
    rd = RawData(source=share_source, data=b'This is just some data')
    rd.save()

    assert RawData.objects.first().data == b'This is just some data'


@pytest.mark.django_db
def test_must_have_data(share_source):
    rd = RawData(source=share_source)

    with pytest.raises(exceptions.ValidationError) as e:
        rd.save()

    assert '"data" on {!r} can not be blank or empty'.format(rd) == e.value.args[0]


@pytest.mark.django_db
def test_must_have_source():
    rd = RawData(data='SomeData')

    with pytest.raises(IntegrityError) as e:
        rd.save()

    assert 'null value in column "source_id" violates not-null constraint' in e.value.args[0]
