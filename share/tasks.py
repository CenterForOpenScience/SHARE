import datetime

import celery

from django.apps import apps

from share.models import RawData


@celery.task
def run_harvester(app_label, started_by=None):
    config = apps.get_app_config(app_label)
    harvester = config.HARVESTER(config)
    harvester.harvest(datetime.timedelta(days=-1), datetime.datetime.utcnow())


@celery.task
def run_normalizer(app_label, started_by=None):
    config = apps.get_app_config(app_label)
    normalizer = config.as_normalizer()

    for block in normalizer.blocks(size=50):
        normalize_block(app_label, block, started_by=started_by)


@celery.task
def normalize_block(app_label, block, started_by=None):
    config = apps.get_app_config(app_label)
    normalizer = config.as_normalizer()

    for raw in RawData.objects.filter(id__in=block):
        normalizer.normalize(raw)
