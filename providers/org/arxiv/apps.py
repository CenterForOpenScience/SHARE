from celery.schedules import crontab

from share.core import ProviderAppConfig

# from .harvester import ArxivHarvester
# from .normalizer import ArxivNormalizer


class ArxivConfig(ProviderAppConfig):
    name = 'providers.org.arxiv'

    title = 'arxiv'
    home_page = ''

    @property
    def harvester(self):
        from .harvester import ArxivHarvester
        return ArxivHarvester

    @property
    def normalizer(self):
        from .normalizer import ArxivNormalizer
        return ArxivNormalizer

    # harvester = ArxivHarvester
    # normalizer = ArxivNormalizer

    schedule = crontab(minute=0, hour=0)
