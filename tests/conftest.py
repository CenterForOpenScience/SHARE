import pytest

from share.models import Person, NormalizedData
from share.models import ShareUser
from share.change import ChangeGraph


@pytest.fixture
def share_source():
    source = ShareUser(username='tester')
    source.save()
    return source

def normalized_data_id(share_source):
    normalized_data = NormalizedData(source=share_source())
    normalized_data.save()
    return normalized_data.id


@pytest.fixture
def john_doe(share_source):
    return Person.objects.create(given_name='John', family_name='Doe')


@pytest.fixture
def jane_doe(share_source):
    return Person.objects.create(given_name='Jane', family_name='Doe')
