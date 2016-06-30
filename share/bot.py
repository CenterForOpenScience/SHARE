import abc
import logging

from celery.schedules import crontab

from share.robot import RobotAppConfig

logger = logging.getLogger(__name__)


class BotAppConfig(RobotAppConfig, metaclass=abc.ABCMeta):

    version = '0.0.0'
    schedule = crontab(minute=0, hour=0)
    task = 'share.tasks.BotTask'
    description = 'TODO'  # TODO

    @property
    def task_name(self):
        return '{} bot task'.format(self.label)

    @property
    def label(self):
        return self.name

    @abc.abstractmethod
    def get_bot(self):
        raise NotImplementedError


class Bot(abc.ABC):

    def __init__(self, config):
        self.config = config

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError
