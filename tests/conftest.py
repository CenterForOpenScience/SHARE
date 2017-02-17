import datetime
import json
import random
import string

import pytest

from django.core.management import call_command
from django.utils import timezone
from django.conf import settings
from oauth2_provider.models import AccessToken, Application

from share.models import Person, NormalizedData, Change, ChangeSet, RawDatum
from share.models import Article, Institution
from share.models import ShareUser
from share.models import Harvester, Transformer, Source, SourceConfig, SourceUniqueIdentifier
from share.change import ChangeGraph


@pytest.fixture
def client():
    from django.test.client import Client

    class JSONAPIClient(Client):
        def _parse_json(self, response, **extra):
            if 'application/vnd.api+json' not in response.get('Content-Type'):
                raise ValueError(
                    'Content-Type header is "{0}", not "application/vnd.api+json"'
                    .format(response.get('Content-Type'))
                )
            return json.loads(response.content.decode(), **extra)

    return JSONAPIClient()


@pytest.fixture(autouse=True)
def apply_test_settings(settings):
    settings.CELERY_ALWAYS_EAGER = True


@pytest.fixture
def trusted_user():
    user = ShareUser(username='trusted_tester', is_trusted=True)
    user.save()
    return user


@pytest.fixture
def robot_user():
    username = 'robot_tester'
    user = ShareUser.objects.create_robot_user(username=username, robot='Tester')
    application_user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
    application = Application.objects.get(user=application_user)
    client_secret = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(64))
    AccessToken.objects.create(
        user=user,
        application=application,
        expires=(timezone.now() + datetime.timedelta(weeks=20 * 52)),  # 20 yrs
        scope=settings.HARVESTER_SCOPES,
        token=client_secret
    )
    return user


@pytest.fixture
def share_user():
    user = ShareUser(username='tester')
    user.save()
    return user


@pytest.fixture
def share_source(share_user):
    source = Source(name='sauce', long_title='Saucy sauce', user=share_user)
    source.save()
    return source


@pytest.fixture
<<<<<<< HEAD
def harvester_model():
    harvester = Harvester(key='testharvester')
    harvester.save()
    return harvester


@pytest.fixture
def transformer_model():
    transformer = Transformer(key='testtransformer')
    transformer.save()
    return transformer


@pytest.fixture
def source_config(share_source, harvester_model, transformer_model):
    config = SourceConfig(
        label='sauce',
        source=share_source,
        base_url='http://example.com',
        harvester=harvester_model,
        transformer=transformer_model
    )
    config.save()
    return config


@pytest.fixture
def suid(source_config):
    suid = SourceUniqueIdentifier(identifier='this is a record', source_config=source_config)
    suid.save()
    return suid


@pytest.fixture
def raw_data(suid):
    raw_data = RawDatum(suid=suid, data={})
    raw_data.save()
    return raw_data


@pytest.fixture
def raw_data_id(raw_data):
    return raw_data.id


@pytest.fixture
def normalized_data(share_user):
    normalized_data = NormalizedData(source=share_user, data={})
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
    return ChangeGraph([{
        '@id': '_:1234',
        '@type': 'person',
        'given_name': 'No',
        'family_name': 'Matter',
    }]).nodes[0]


@pytest.fixture
def change_factory(share_user, change_set, change_node):
    class ChangeFactory:
        def from_graph(self, graph, disambiguate=False):
            nd = NormalizedData.objects.create(data=graph, source=share_user)
            cg = ChangeGraph(graph['@graph'])
            cg.process(disambiguate=disambiguate)
            return ChangeSet.objects.from_graph(cg, nd.pk)

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
def john_doe(change_ids):
    john = Person.objects.create(given_name='John', family_name='Doe', change_id=change_ids.get())
    john.refresh_from_db()
    return john


@pytest.fixture
def jane_doe(change_ids):
    jane = Person.objects.create(given_name='Jane', family_name='Doe', change_id=change_ids.get())
    jane.refresh_from_db()
    return jane


@pytest.fixture
def all_about_anteaters(change_ids):
    return Article.objects.create(title='All about Anteaters', change_id=change_ids.get())


@pytest.fixture
def university_of_whales(change_ids):
    return Institution.objects.create(name='University of Whales', change_id=change_ids.get())


@pytest.fixture
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'tests/initial-data.yaml')
