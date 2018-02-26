import logging

import celery

import pendulum

from django.apps import apps
from django.conf import settings
from django.db import models

from elasticsearch import Elasticsearch
from elasticsearch import helpers

from share.models import AbstractCreativeWork
from share.models import CeleryTaskResult
from share.models import WorkIdentifier
from share.search import indexing

from bots.elasticsearch.bot import ElasticSearchBot


logger = logging.getLogger(__name__)


def safe_substr(value, length=32000):
    if value:
        return str(value)[:length]
    return None


@celery.shared_task(bind=True)
def update_elasticsearch(self, filter=None, index=None, models=None, setup=False, url=None, to_daemon=True, periodic=True):
    """
    """
    if periodic:
        dupe_task_qs = CeleryTaskResult.objects.filter(
            task_name=self.name,
            status=celery.states.STARTED
        ).exclude(task_id=self.request.id)

        if dupe_task_qs.exists():
            logger.info('Another %s task is already running; let it work alone.', self.name)
            return

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
    # TODO This method should not have to exist anymore
    es_client = Elasticsearch(es_url or settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=settings.ELASTICSEARCH_TIMEOUT)
    action_gen = indexing.ElasticsearchActionGenerator([settings.ELASTICSEARCH_INDEX], [indexing.FakeMessage(model_name, ids)])
    stream = helpers.streaming_bulk(es_client, (x for x in action_gen if x), max_chunk_bytes=10 * 1024 ** 2, raise_on_error=False)

    for ok, resp in stream:
        if not ok and not (resp.get('delete') and resp['delete']['status'] == 404):
            raise ValueError(resp)


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


def count_es(es_url, es_index, min_date, max_date):
    es_client = Elasticsearch(es_url or settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=settings.ELASTICSEARCH_TIMEOUT)

    return es_client.count(
        index=(es_index or settings.ELASTICSEARCH_INDEX),
        doc_type='creativeworks',
        body={
            'query': {
                'range': {
                    'date_created': {'gte': min_date.isoformat(), 'lte': max_date.isoformat()}
                }
            }
        }
    )['count']


def count_db(min_date, max_date):
    sqs = WorkIdentifier.objects.filter(creative_work=models.OuterRef('pk')).annotate(cnt=models.Count('*')).values('cnt')
    sqs.query.group_by = []  # Because Django is soooo "smart"

    qs = AbstractCreativeWork.objects.annotate(
        identifiers_count=models.Subquery(sqs)
    ).exclude(title='').exclude(is_deleted=True).filter(
        # Range test (inclusive).
        # Filtering a DateTimeField with dates won’t include items on the last day, because the bounds are interpreted as “0am on the given date”
        # - Django Docs
        date_created__range=[min_date, max_date],
        # NOTE: lt 51 is taken from share/search/fetchers.py
        identifiers_count__lt=51,
    )

    return qs.count()


@celery.task(bind=True)
def pseudo_bisection(self, es_url, es_index, min_date, max_date, dry=False, to_daemon=False):
    """Checks if the database count matches the ES count

    If counts differ, split the date range in half and check counts in smaller ranges
    Pseudo binary because it can't throw away half the results based on the middle value

    """
    MAX_DB_COUNT = 500
    MIN_MISSING_RATIO = 0.7

    min_date = pendulum.parse(min_date)
    max_date = pendulum.parse(max_date)

    logger.debug('Checking counts for %s to %s', min_date.format('%B %-d, %Y %I:%M:%S %p'), max_date.format('%B %-d, %Y %I:%M:%S %p'))

    db_count = count_db(min_date, max_date)
    es_count = count_es(es_url, es_index, min_date, max_date)

    if db_count == es_count:
        logger.info('Counts for %s to %s match at %d', min_date.format('%B %-d, %Y %I:%M:%S %p'), max_date.format('%B %-d, %Y %I:%M:%S %p'), es_count)
        return

    logger.warning(
        'Counts for %s to %s do not match. %s creativeworks in ES, %s creativeworks in database. Difference of %d',
        min_date.format('%B %-d, %Y %I:%M:%S %p'),
        max_date.format('%B %-d, %Y %I:%M:%S %p'),
        es_count,
        db_count,
        db_count - es_count,
    )

    if db_count <= MAX_DB_COUNT or 1 - abs(es_count / db_count) >= MIN_MISSING_RATIO:
        logger.debug('Met the threshold of %d total works to index or %d%% missing works.', MAX_DB_COUNT, MIN_MISSING_RATIO * 100)

        logger.error('Reindexing records created from %s to %s.', min_date.format('%B %-d, %Y %I:%M:%S %p'), max_date.format('%B %-d, %Y %I:%M:%S %p'))

        if dry:
            logger.debug('dry=True, not reindexing missing works')
            return

        logger.debug('dry=False, reindexing missing works')
        task = update_elasticsearch.apply_async((), {
            'filter': {'date_created__range': [min_date, max_date]},
            'to_daemon': to_daemon,
            'models': ['creativework'],
            'periodic': False,
        })
        logger.info('Spawned %r', task)
        return

    logger.debug('Did NOT meet the threshold of %d total works to index or %d%% missing works.', MAX_DB_COUNT, MIN_MISSING_RATIO * 100)

    median_date = min_date.copy().average(max_date)

    for (_min, _max) in [(min_date, median_date), (median_date, max_date)]:
        logger.info('Starting bisection of %s to %s', _min.format('%B %-d, %Y %I:%M:%S %p'), _max.format('%B %-d, %Y %I:%M:%S %p'))

        targs, tkwargs = (es_url, es_index, str(_min), str(_max)), {'dry': dry, 'to_daemon': to_daemon}

        if getattr(self.request, 'is_eager', False):
            logger.debug('Running in an eager context. Running child tasks synchronously.')
            pseudo_bisection.apply(targs, tkwargs)
        else:
            pseudo_bisection.apply_async(targs, tkwargs)


@celery.shared_task(bind=True)
def elasticsearch_janitor(self, es_url=None, es_index=None, dry=False, to_daemon=True):
    """
    Looks for discrepancies between postgres and elastic search numbers
    Re-indexes time periods that differ in count

    """
    # get range of date_created in database; assumes current time is the max
    logger.debug('Starting Elasticsearch JanitorTask')

    min_date = AbstractCreativeWork.objects.all().aggregate(models.Min('date_created'))['date_created__min']
    if not min_date:
        logger.warning('No CreativeWorks are present in Postgres. Exiting')
        return

    max_date = pendulum.utcnow()
    min_date = pendulum.instance(min_date)

    pseudo_bisection.apply((es_url, es_index, str(min_date), str(max_date)), {'dry': dry, 'to_daemon': to_daemon}, throw=True)
