import logging

import celery

import pendulum

from django.apps import apps
from django.conf import settings
from django.db.models import Min
from elasticsearch import Elasticsearch
from elasticsearch import helpers

from share.models import CreativeWork
from share.search import indexing

from bots.elasticsearch.bot import ElasticSearchBot


logger = logging.getLogger(__name__)


def safe_substr(value, length=32000):
    if value:
        return str(value)[:length]
    return None


@celery.shared_task(bind=True)
def update_elasticsearch(self, filter=None, index=None, models=None, setup=False, url=None, to_daemon=False):
    """
    """
    # TODO Refactor Elasitcsearch logic
    ElasticSearchBot(
        es_filter=filter,
        es_index=index,
        es_models=models,
        es_setup=setup,
        es_url=url,
        to_daemon=to_daemon,
    ).run()


@celery.shared_task(bind=True)
def index_model(self, model_name, ids, es_url=None, es_index=None):
    es_client = Elasticsearch(es_url or settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=settings.ELASTICSEARCH_TIMEOUT)
    indexing.ESIndexer(es_client, es_index or settings.ELASTICSEARCH_INDEX, indexing.FakeMessage(model_name, ids)).index()


@celery.shared_task(bind=True)
def index_sources(self, es_index=None, es_url=None, timeout=None):
    errors = []
    es_client = Elasticsearch(es_url or settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=settings.ELASTICSEARCH_TIMEOUT)

    for ok, resp in helpers.streaming_bulk(es_client, SourceBulkStreamHelper(es_index or settings.ELASTICSEARCH_INDEX), raise_on_error=False):
        if not ok:
            logger.warning(resp)
        else:
            logger.debug(resp)

        if not ok and not (resp.get('delete') and resp['delete']['status'] == 404):
            errors.append(resp)

    if errors:
        raise Exception('Failed to index documents {}'.format(errors))


class SourceBulkStreamHelper:

    def __init__(self, es_index):
        self.es_index = es_index

    def __iter__(self):
        Source = apps.get_model('share.Source')
        opts = {'_index': self.es_index, '_type': 'sources'}

        for source in Source.objects.all():
            # remove sources from search that don't appear on the sources page
            if not source.icon or source.is_deleted:
                yield {'_op_type': 'delete', '_id': source.name, **opts}
            else:
                yield {'_op_type': 'index', '_id': source.name, **self.serialize(source), **opts}

    def serialize(self, source):
        return {
            'id': source.name,
            'type': 'source',
            'name': safe_substr(source.long_title),
            'short_name': safe_substr(source.name)
        }


def check_counts_in_range(es_url, es_index, min_date, max_date):
    es_client = Elasticsearch(es_url or settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=settings.ELASTICSEARCH_TIMEOUT)
    partial_database_count = CreativeWork.objects.exclude(title='').exclude(is_deleted=True).filter(
        date_created__range=[min_date, max_date]
    ).count()
    partial_es_count = es_client.count(
        index=(es_index or settings.ELASTICSEARCH_INDEX),
        doc_type='creativeworks',
        body={
            'query': {
                'range': {
                    'date_created': {'gte': min_date, 'lte': max_date}
                }
            }
        }
    )['count']
    return (partial_database_count == partial_es_count, partial_database_count, partial_es_count)


def get_date_range_parts(min_date, max_date):
    middle_date = pendulum.parse(min_date).average(pendulum.parse(max_date))
    return {
        'first_half': {'min_date': min_date, 'max_date': middle_date.isoformat()},
        'second_half': {'min_date': middle_date.isoformat(), 'max_date': max_date}
    }


@celery.task(bind=True)
def pseudo_bisection(self, es_url, es_index, min_date, max_date, dry=False, to_daemon=False):
    """Checks if the database count matches the ES count

    If counts differ, split the date range in half and check counts in smaller ranges
    Pseudo binary because it can't throw away half the results based on the middle value

    """
    MAX_DB_COUNT = 500
    MIN_MISSING_RATIO = 0.7

    logger.debug(
        'Checking counts for %s to %s',
        pendulum.parse(min_date).format('%B %-d, %Y %I:%M:%S %p'),
        pendulum.parse(max_date).format('%B %-d, %Y %I:%M:%S %p'),
    )

    counts_match, db_count, es_count = check_counts_in_range(es_url, es_index, min_date, max_date)

    if counts_match:
        logger.info(
            'Counts for %s to %s match. %s creativeworks in ES, %s creativeworks in database.',
            pendulum.parse(min_date).format('%B %-d, %Y %I:%M:%S %p'),
            pendulum.parse(max_date).format('%B %-d, %Y %I:%M:%S %p'),
            es_count,
            db_count
        )
        return

    logger.warning(
        'Counts for %s to %s do not match. %s creativeworks in ES, %s creativeworks in database.',
        pendulum.parse(min_date).format('%B %-d, %Y %I:%M:%S %p'),
        pendulum.parse(max_date).format('%B %-d, %Y %I:%M:%S %p'),
        es_count,
        db_count
    )

    if db_count <= MAX_DB_COUNT or 1 - abs(es_count / db_count) >= MIN_MISSING_RATIO:
        logger.debug('Met the threshold of %d total works to index or %d%% missing works.', MAX_DB_COUNT, MIN_MISSING_RATIO * 100)

        logger.info(
            'Reindexing records created from %s to %s.',
            pendulum.parse(min_date).format('%B %-d, %Y %I:%M:%S %p'),
            pendulum.parse(max_date).format('%B %-d, %Y %I:%M:%S %p')
        )

        if dry:
            logger.debug('dry=True, not reindexing missing works')
            return

        logger.debug('dry=False, reindexing missing works')
        task = update_elasticsearch.apply_async((), {'to_daemon': to_daemon, 'filter': {'date_created__range': [min_date, max_date]}})
        logger.info('Spawned %r', task)
        return

    logger.debug('Did NOT meet the threshold of %d total works to index or %d%% missing works.', MAX_DB_COUNT, MIN_MISSING_RATIO * 100)

    for key, value in get_date_range_parts(min_date, max_date).items():
        logger.info(
            'Starting bisection of %s to %s',
            pendulum.parse(value['min_date']).format('%B %-d, %Y %I:%M:%S %p'),
            pendulum.parse(value['max_date']).format('%B %-d, %Y %I:%M:%S %p')
        )

        targs, tkwargs = (es_url, es_index, value['min_date'], value['max_date']), {'dry': dry}

        if getattr(self.request, 'is_eager', False):
            logger.debug('Running in an eager context. Running child tasks synchronously.')
            pseudo_bisection.apply(targs, tkwargs)
            return

        pseudo_bisection.apply_async(targs, tkwargs)
        return


@celery.shared_task(bind=True)
def elasticsearch_janitor(self, es_url=None, es_index=None, dry=False, to_daemon=False):
    """
    Looks for discrepancies between postgres and elastic search numbers
    Re-indexes time periods that differ in count

    """
    # get range of date_created in database; assumes current time is the max
    logger.debug('Starting Elasticsearch JanitorTask')

    min_date = CreativeWork.objects.all().aggregate(Min('date_created'))['date_created__min']
    if not min_date:
        logger.warning('No CreativeWorks are present in Postgres. Exiting')
        return

    max_date = pendulum.utcnow()
    min_date = pendulum.instance(min_date)

    pseudo_bisection.apply((es_url, es_index, min_date.isoformat(), max_date.isoformat()), {'dry': dry, 'to_daemon': to_daemon}, throw=True)
