import pytest

from share.models import Person, NormalizedData, Change, ChangeSet
from share.models import ShareUser
from share.change import ChangeNode, ChangeGraph


@pytest.fixture
def share_source():
    source = ShareUser(username='tester')
    source.save()
    return source


@pytest.fixture
def normalized_data(share_source):
    normalized_data = NormalizedData(source=share_source)
    normalized_data.save()
    return normalized_data


@pytest.fixture
def normalized_data_id(normalized_data):
    return normalized_data.id


@pytest.fixture
def change_set(normalized_data_id):
    return ChangeSet.objects.create(normalized_data_id=normalized_data_id)


@pytest.fixture
def change_node():
    return ChangeNode.from_jsonld({
        '@id': '_:1234',
        '@type': 'person',
        'given_name': 'No',
        'family_name': 'Matter',
    }, disambiguate=False)


@pytest.fixture
def change_factory(share_source, change_set, change_node):
    class ChangeFactory:
        def from_graph(self, graph, disambiguate=False):
            nd = NormalizedData.objects.create(normalized_data=graph, source=share_source)
            return ChangeSet.objects.from_graph(
                ChangeGraph.from_jsonld(
                    graph,
                    disambiguate=disambiguate,
                ),
                nd.pk
            )

        def get(self):
            return Change.objects.from_node(change_node, change_set)

    return ChangeFactory()


@pytest.fixture
def change_ids(change_factory):
    class ChangeIdFactory:
        def get(self):
            return change_factory.get().id
    return ChangeIdFactory()


@pytest.fixture
def john_doe(share_source, change_ids):
    return Person.objects.create(given_name='John', family_name='Doe', change_id=change_ids.get())


@pytest.fixture
def jane_doe(share_source, change_ids):
    return Person.objects.create(given_name='Jane', family_name='Doe', change_id=change_ids.get())
