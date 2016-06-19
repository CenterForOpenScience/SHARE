import datetime

import celery

from django.apps import apps

from share.models import RawData


@celery.task
def run_harvester(app_label, start=None, end=None, started_by=None):
    if not start and not end:
        start, end = datetime.timedelta(days=-1), datetime.datetime.utcnow()
    config = apps.get_app_config(app_label)
    harvester = config.harvester(config)
    harvester.harvest(start, end)


@celery.task
def run_normalizer(app_label, started_by=None):
    config = apps.get_app_config(app_label)
    normalizer = config.normalizer(config)

    for block in normalizer.blocks(size=50):
        normalize_block(app_label, block, started_by=started_by)


@celery.task
def normalize_block(app_label, block, started_by=None):
    config = apps.get_app_config(app_label)
    normalizer = config.normalizer(config)

    for raw in RawData.objects.filter(id__in=block):
        normalizer.normalize(raw)
