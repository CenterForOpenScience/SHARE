import json
import logging
import datetime
from time import sleep

import celery

from django.apps import apps
from django.contrib.auth.models import User

from share.models import RawData, NormalizedManuscript

logger = logging.getLogger(__name__)


@celery.task(bind=True)
def run_harvester(self, app_label, start=None, end=None, started_by=None):
    if not start and not end:
        start, end = datetime.timedelta(days=-1), datetime.datetime.utcnow()
    config = apps.get_app_config(app_label)
    harvester = config.harvester(config)

    try:
        logger.info('Starting harvester run for {} {} - {}'.format(app_label, start, end))
        raws = harvester.harvest(start, end)
        logger.info('Collected {} data blobs from {}'.format(len(raws), app_label))
    except Exception as e:
        raise self.retry(countdown=10, exc=e)

    for raw in raws:
        task = run_normalizer.apply_async((app_label, raw.pk,), {'started_by': started_by})
        logger.debug('Started run_normalizer task {} for {}'.format(task, raw.id))


@celery.task(bind=True)
def run_normalizer(self, app_label, raw_id, started_by=None):
    raw = RawData.objects.get(pk=raw_id)
    config = apps.get_app_config(app_label)
    normalizer = config.normalizer(config)

    try:
        logger.info('Starting normalization for {} by {}'.format(raw, normalizer))
        graph = normalizer.normalize(raw)
        logger.debug('Parsed {} into {}'.format(raw, json.dumps(graph, indent=2)))
    except Exception as e:
        raise self.retry(countdown=10, exc=e)

@celery.task()
def make_json_patches(normalized_id, started_by_id=None):
    started_by = None
    normalized = NormalizedManuscript.objects.get(pk=normalized_id)
    if started_by_id:
        started_by = User.objects.get(pk=started_by_id)
    logger.info('{} started make JSON patches for {} at {}'.format(started_by, normalized, datetime.datetime.utcnow().isoformat()))
    sleep(10)
    logger.info('Finished make JSON patches for {} by {} at {}'.format(normalized, started_by, datetime.datetime.utcnow().isoformat()))
