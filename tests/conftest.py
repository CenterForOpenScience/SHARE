import pytest

from share.models import Person
from share.models import ShareUser
from share.change import ChangeGraph


@pytest.fixture
def share_source():
    source = ShareUser(username='tester')
    source.save()
    return source


@pytest.fixture
def john_doe(share_source):
    return Person.objects.create(given_name='John', family_name='Doe')


@pytest.fixture
def jane_doe(share_source):
    return Person.objects.create(given_name='Jane', family_name='Doe')
