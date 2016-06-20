import json
import logging
import datetime

import celery

from django.apps import apps

from share.models import RawData


logger = logging.getLogger(__name__)


@celery.task
def run_harvester(app_label, start=None, end=None, started_by=None):
    if not start and not end:
        start, end = datetime.timedelta(days=-1), datetime.datetime.utcnow()
    config = apps.get_app_config(app_label)
    harvester = config.harvester(config)

    logger.info('Starting harvester run for {} {} - {}'.format(app_label, start, end))
    raws = harvester.harvest(start, end)
    logger.info('Collected {} data blobs from {}'.format(len(raws), app_label))

    for raw in raws:
        task = run_normalizer.apply_async((app_label, raw.pk,), {'started_by': started_by})
        logger.debug('Started run_normalizer task {} for {}'.format(task, raw.id))


@celery.task
def run_normalizer(app_label, raw_id, started_by=None):
    raw = RawData.objects.get(pk=raw_id)
    config = apps.get_app_config(app_label)
    normalizer = config.normalizer(config)

    logger.info('Starting normalization for {} by {}'.format(raw, normalizer))
    graph = normalizer.normalize(raw)
    logger.debug('Parsed {} into {}'.format(raw, json.dumps(graph, indent=2)))
