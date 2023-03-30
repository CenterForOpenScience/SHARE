import datetime
import json
import logging
import random
import string

import pytest

from django.db import transaction
from django.utils import timezone

from oauth2_provider.models import AccessToken, Application

from share.models import NormalizedData, RawDatum
from share.models import ShareUser
from share.models import SourceUniqueIdentifier

from tests import factories
from tests.share.normalize.factories import GraphBuilder


logger = logging.getLogger(__name__)


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
def robot_user(settings):
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
def system_user(settings):
    return ShareUser.objects.get(username=settings.APPLICATION_USERNAME)


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
def Graph():
    return GraphBuilder()


@pytest.fixture
def ExpectedGraph(Graph):
    def expected_graph(*args, **kwargs):
        return Graph(*args, **kwargs, normalize_fields=True)
    return expected_graph


def rolledback_transaction(loglabel):
    class ExpectedRollback(Exception):
        pass
    try:
        with transaction.atomic():
            print(f'{loglabel}: started transaction')
            yield
            raise ExpectedRollback('this is an expected rollback; all is well')
    except ExpectedRollback:
        print(f'{loglabel}: rolled back transaction (as planned)')
    else:
        raise ExpectedRollback('expected a rollback but did not get one; something is wrong')


@pytest.fixture(scope='class')
def class_scoped_django_db(django_db_setup, django_db_blocker, request):
    """a class-scoped version of the `django_db` mark
    (so we can use class-scoped fixtures to set up data
    for use across several tests)

    recommend using via the `nested_django_db` fixture,
    or use directly in another class-scoped fixture.
    """
    with django_db_blocker.unblock():
        yield from rolledback_transaction(f'class_scoped_django_db({request.node})')


@pytest.fixture(scope='function')
def nested_django_db(class_scoped_django_db, request):
    """wrap each function and the entire class in transactions
    (so fixtures can have scope='class' for reuse across tests,
    but what happens in each test stays in that test)

    recommend using via the `nested_django_db` mark
    """
    yield from rolledback_transaction(f'nested_django_db({request.node})')
