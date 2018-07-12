import datetime
import json
import random
import string

import pytest

from django.apps import apps
from django.utils import timezone
from django.db import connections
from django.db import transaction
from django.conf import settings
from django.db.models.signals import post_save

from oauth2_provider.models import AccessToken, Application
from urllib3.connection import ConnectionError
from elasticsearch.exceptions import ConnectionError as ElasticConnectionError

from share.ingest.change_builder import ChangeBuilder
from share.models import Person, NormalizedData, ChangeSet, RawDatum
from share.models import Article, Institution
from share.models import ShareUser
from share.models import SourceUniqueIdentifier
from share.regulate import Regulator
from share.util.graph import MutableGraph
from bots.elasticsearch.bot import ElasticSearchBot
from tests import factories


def pytest_configure(config):
    # The hackiest of all hacks
    # Looks like pytest's recursion detection doesn't like typedmodels
    # and will sometimes cause all tests to fail
    # If we create a queryset here, all of typedmodels cached properties
    # will be filled in while recursion detection isn't active
    Article.objects.all()
    if config.option.usepdb:
        try:
            import IPython.core.debugger  # noqa
        except ImportError:
            return
        else:
            config.option.usepdb_cls = 'IPython.core.debugger:Pdb'


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
    user = ShareUser(
        username='tester',
    )
    user.save()

    # add source
    factories.SourceFactory(user=user),
    return user


@pytest.fixture
def source(share_user):
    return share_user.source


@pytest.fixture
def source_config():
    return factories.SourceConfigFactory()


@pytest.fixture
def suid(source_config):
    suid = SourceUniqueIdentifier(identifier='this is a record', source_config=source_config)
    suid.save()
    return suid


@pytest.fixture
def raw_data(suid):
    raw_data = RawDatum(suid=suid, datum='{}')
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
    return next(n for n in MutableGraph.from_jsonld([{
        '@id': '_:1234',
        '@type': 'person',
        'given_name': 'No',
        'family_name': 'Matter',
    }]))


@pytest.fixture
def ingest(normalized_data):
    def _ingest(graph, disambiguate=True, user=None, save=True):
        Regulator().regulate(graph)

        nd = factories.NormalizedDataFactory(source=user) if user else normalized_data
        cs = ChangeBuilder.build_change_set(graph, nd, disambiguate=disambiguate)
        if save and cs is not None:
            cs.accept()
        return cs
    return _ingest


@pytest.fixture
def change_factory(share_user, source, change_set, change_node):
    class ChangeFactory:
        def from_graph(self, jsonld, disambiguate=False):
            nd = NormalizedData.objects.create(data=jsonld, source=share_user)
            graph = MutableGraph.from_jsonld(jsonld)
            return ChangeBuilder.build_change_set(graph, nd, disambiguate=disambiguate)

        def get(self):
            return ChangeBuilder(change_node, source).build_change(change_set)

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
def all_about_anteaters(change_ids, share_user):
    article = Article.objects.create(title='All about Anteaters', change_id=change_ids.get())
    article.sources.add(share_user)
    return article


@pytest.fixture
def university_of_whales(change_ids):
    return Institution.objects.create(name='University of Whales', change_id=change_ids.get())


@pytest.fixture
def elastic(settings):
    settings.ELASTICSEARCH['TIMEOUT'] = 5
    settings.ELASTICSEARCH['INDEX'] = 'test_' + settings.ELASTICSEARCH['INDEX']

    bot = ElasticSearchBot(es_setup=False)

    try:
        bot.es_client.indices.delete(index=settings.ELASTICSEARCH['INDEX'], ignore=[400, 404])

        bot.setup()
    except (ConnectionError, ElasticConnectionError):
        raise pytest.skip('Elasticsearch unavailable')

    yield bot

    bot.es_client.indices.delete(index=settings.ELASTICSEARCH['INDEX'], ignore=[400, 404])


@pytest.fixture
def transactional_db(django_db_blocker, request):
    # Django's/Pytest Django's handling of this is garbage
    # The database is wipe of initial data and never repopulated so we have to do
    # all of it ourselves
    django_db_blocker.unblock()
    request.addfinalizer(django_db_blocker.restore)

    from django.test import TransactionTestCase
    test_case = TransactionTestCase(methodName='__init__')
    test_case._pre_setup()

    # Dump all initial data into a string :+1:
    for connection in connections.all():
        if connection.settings_dict['TEST']['MIRROR']:
            continue
        connection._test_serialized_contents = connection.creation.serialize_db_to_string()

    yield None

    test_case.serialized_rollback = True
    test_case._post_teardown()

    # Disconnect post save listeners because they screw up deserialization
    receivers, post_save.receivers = post_save.receivers, []

    if test_case.available_apps is not None:
        apps.unset_available_apps()

    for connection in connections.all():
        if connection.settings_dict['TEST']['MIRROR']:
            connection.close()
            continue
        # Everything has to be in a single transaction to avoid violating key constraints
        # It also makes it run significantly faster
        with transaction.atomic():
            connection.creation.deserialize_db_from_string(connection._test_serialized_contents)

    if test_case.available_apps is not None:
        apps.set_available_apps(test_case.available_apps)

    post_save.receivers = receivers


@pytest.fixture
def celery_app(celery_app):
    """Probably won't want to use this.
    The worker that is spawned will not have access to the test transaction.
    Leaving this here, just in case. Making it work properly takes some effort.
    """
    from celery import signals
    from project.celery import app
    # There's a Django fix up closes the django connection on most events.
    # The actual celery app causes it to be registered so we have to manually disable it here
    signals.worker_init.disconnect(app._fixups[0].on_worker_init)
    # Finally, when the test celery app runs the fixup we allow it have 1 resuable connection.
    celery_app.conf.CELERY_DB_REUSE_MAX = 1
    celery_app.autodiscover_tasks(['share'])
    return celery_app


@pytest.fixture
def no_celery():
    from project.celery import app
    app.conf.task_always_eager = True
