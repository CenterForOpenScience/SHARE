import datetime
import celery

from django.apps import apps


@celery.task
def run_harvester(app_label):
    config = apps.get_app_config(app_label)
    harvester = config.HARVESTER(config)
    harvester.harvest(datetime.timedelta(days=-1), datetime.datetime.utcnow())
