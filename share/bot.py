import abc
import logging

import arrow
from celery.schedules import crontab
from django.utils.functional import cached_property

from share.robot import RobotAppConfig

logger = logging.getLogger(__name__)


class BotAppConfig(RobotAppConfig, metaclass=abc.ABCMeta):

    schedule = crontab(minute=0, hour=0)
    task = 'share.tasks.BotTask'
    description = 'TODO'  # TODO

    @property
    def task_name(self):
        return '{} bot task'.format(self.label)

    @property
    def label(self):
        return self.name.rpartition('bots.')[2]

    @abc.abstractmethod
    def get_bot(self, started_by, last_run=None):
        raise NotImplementedError


class Bot(abc.ABC):

    def __init__(self, config, started_by, last_run=None):
        self.started_by = started_by
        self.config = config
        self._last_run = last_run

    @cached_property
    def last_run(self) -> arrow.Arrow:
        from share.models import CeleryProviderTask

        if self._last_run is not None:
            last_run = arrow.get(self._last_run)
        else:
            logger.debug('Finding last successful job')
            last_run = CeleryProviderTask.objects.filter(
                app_label=self.config.label,
                status=CeleryProviderTask.STATUS.succeeded,
            ).order_by(
                '-timestamp'
            ).values_list('timestamp', flat=True).first()
            if last_run:
                last_run = arrow.get(last_run)
            else:
                last_run = arrow.get(0)
            logger.info('Found last job %s', last_run)

        logger.info('Using last run of %s', last_run)
        return last_run

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError
