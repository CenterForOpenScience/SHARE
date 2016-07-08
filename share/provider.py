import abc
import logging

from celery.schedules import crontab

from share.robot import RobotAppConfig
from share.harvest.oai import OAIHarvester
from share.normalize import Normalizer
from share.normalize.oai import OAINormalizer

logger = logging.getLogger(__name__)


class ProviderAppConfig(RobotAppConfig, metaclass=abc.ABCMeta):

    schedule = crontab(minute=0, hour=0)
    task = 'share.tasks.HarvesterTask'
    description = 'TODO'  # TODO

    @abc.abstractproperty
    def title(self):
        raise NotImplementedError

    @abc.abstractproperty
    def long_title(self):
        raise NotImplementedError

    @abc.abstractproperty
    def home_page(self):
        raise NotImplementedError

    @abc.abstractproperty
    def harvester(self):
        raise NotImplementedError

    @property
    def label(self):
        return self.name.rpartition('providers.')[2]

    @abc.abstractproperty
    def version(self):
        raise NotImplementedError

    @property
    def task_name(self):
        return '{} harvester task'.format(self.label)

    @property
    def normalizer(self):
        return Normalizer


class OAIProviderAppConfig(ProviderAppConfig, metaclass=abc.ABCMeta):

    rate_limit = (5, 1)
    approved_sets = None
    property_list = []
    emitted_type = 'CreativeWork'

    @abc.abstractproperty
    def url(self):
        return NotImplementedError

    @property
    def harvester(self):
        return OAIHarvester

    @property
    def normalizer(self):
        return OAINormalizer
