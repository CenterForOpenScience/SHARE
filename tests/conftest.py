import datetime
import json
import random
import string

import pytest

from django.utils import timezone

from oauth2_provider.models import AccessToken, Application
from urllib3.connection import ConnectionError
from elasticsearch.exceptions import ConnectionError as ElasticConnectionError

from share.models import NormalizedData, RawDatum
from share.models import ShareUser
from share.models import SourceUniqueIdentifier
from share.models import FormattedMetadataRecord
from share.search import MessageType, SearchIndexer
from share.search.elastic_manager import ElasticManager

from tests import factories
from tests.share.normalize.factories import GraphBuilder


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


@pytest.fixture
def elastic_test_index_name():
    return 'test_share'


@pytest.fixture
def elastic_test_manager(settings, elastic_test_index_name):
    # ideally these settings changes would be encapsulated by ElasticManager, but there's
    # still code that uses the settings directly, so using the pytest-django fixture for now
    settings.ELASTICSEARCH = {
        **settings.ELASTICSEARCH,
        'TIMEOUT': 5,
        'PRIMARY_INDEX': elastic_test_index_name,
        'LEGACY_INDEX': elastic_test_index_name,
        'BACKCOMPAT_INDEX': elastic_test_index_name,
        'ACTIVE_INDEXES': [elastic_test_index_name],
        'INDEXES': {
            elastic_test_index_name: {
                'DEFAULT_QUEUE': f'{elastic_test_index_name}_queue',
                'URGENT_QUEUE': f'{elastic_test_index_name}_queue.urgent',
                'INDEX_SETUP': 'postrend_backcompat',
            },
        },
    }
    elastic_manager = ElasticManager()
    try:
        elastic_manager.delete_index(elastic_test_index_name)
        elastic_manager.create_index(elastic_test_index_name)

        yield elastic_manager

    except (ConnectionError, ElasticConnectionError):
        raise pytest.skip('Elasticsearch unavailable')
    finally:
        elastic_manager.delete_index(elastic_test_index_name)


@pytest.fixture
def index_records(elastic_test_manager):

    def _index_records(normalized_graphs):
        normalized_datums = [
            factories.NormalizedDataFactory(
                data=GraphBuilder()(ng).to_jsonld(),
                raw=factories.RawDatumFactory(
                    datum='',
                ),
            )
            for ng in normalized_graphs
        ]
        suids = [nd.raw.suid for nd in normalized_datums]
        for normd, suid in zip(normalized_datums, suids):
            FormattedMetadataRecord.objects.save_formatted_records(
                suid=suid,
                record_formats=['sharev2_elastic'],
                normalized_datum=normd,
            )
        indexer = SearchIndexer(elastic_manager=elastic_test_manager)
        indexer.handle_messages_sync(MessageType.INDEX_SUID, [suid.id for suid in suids])
        return normalized_datums

    return _index_records
