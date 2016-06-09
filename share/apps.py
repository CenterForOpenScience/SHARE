import logging

from django.apps import apps
from django.apps import AppConfig
from django.conf import settings

import celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)


class ShareConfig(AppConfig):
    name = 'share'

    def ready(self):
        for dapp in apps.get_app_configs():
            harvester = getattr(dapp, 'HARVESTER', None)
            if not harvester:
                if dapp.name.startswith('harvesters.'):
                    logger.warning('App {} does not specify a harvester but is in the harvesters module'.format(dapp))
                continue
            celery.current_app.conf['CELERYBEAT_SCHEDULE']['run_{}'.format(dapp.name)] = {
                'task': 'share.tasks.run_harvester',
                'schedule': crontab(minute=0, hour=0),
                'args': (dapp.name,),
            }
