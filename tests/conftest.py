import pytest

# from share.models import ShareSource
# from share.change import ChangeGraph


@pytest.fixture
@pytest.mark.db
def share_source():
    source = ShareSource(name='tester')
    source.save()
    return source


@pytest.fixture
@pytest.mark.db
def john_doe(share_source):
    return ChangeGraph({
        '@graph': [{
            '@id': '_:1',
            '@type': 'Person',
            'given_name': 'John',
            'family_name': 'Doe',
        }]
    }).change_set(share_source).changes.first().accept()


@pytest.fixture
@pytest.mark.db
def jane_doe(share_source):
    return ChangeGraph({
        '@graph': [{
            '@id': '_:2',
            '@type': 'Person',
            'given_name': 'Jane',
            'family_name': 'Doe',
        }]
    }).change_set(share_source).changes.first().accept()
