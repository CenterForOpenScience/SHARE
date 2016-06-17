from celery.schedules import crontab

from share.core import ProviderAppConfig

from .harvester import FigshareHarvester
from .normalizer import FigshareNormalizer


class FigshareConfig(ProviderAppConfig):
    name = 'providers.com.figshare'

    title = 'figshare'
    home_page = 'https://figshare.com/'

    harvester = FigshareHarvester
    normalizer = FigshareNormalizer

    schedule = crontab(minute=0, hour=0)
