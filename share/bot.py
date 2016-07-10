import abc
import logging

from celery.schedules import crontab

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
    def get_bot(self, started_by):
        raise NotImplementedError


class Bot(abc.ABC):

    def __init__(self, config, started_by):
        self.started_by = started_by
        self.config = config

    @abc.abstractmethod
    def run(self, last_run):
        raise NotImplementedError
