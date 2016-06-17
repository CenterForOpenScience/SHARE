from celery.schedules import crontab

from share.core import ProviderAppConfig


class FigshareConfig(ProviderAppConfig):
    name = 'providers.com.figshare'

    title = 'figshare'
    home_page = 'https://figshare.com/'

    @property
    def harvester(self):
        from .harvester import FigshareHarvester
        return FigshareHarvester

    @property
    def normalizer(self):
        from .normalizer import FigshareNormalizer
        return FigshareNormalizer

    # harvester = FigshareHarvester
    # normalizer = FigshareNormalizer

    schedule = crontab(minute=0, hour=0)
