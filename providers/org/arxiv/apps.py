from celery.schedules import crontab

from share.core import ProviderAppConfig


class ArxivConfig(ProviderAppConfig):
    name = 'providers.org.arxiv'
    TITLE = 'arxiv'
    SCHEDULE = crontab(minute=0, hour=0)

    def ready(self):
        from providers.org.arxiv.harvester import ArxivHarvester
        from providers.org.arxiv.normalizer import ArxivNormalizer
        self.HARVESTER = ArxivHarvester
        self.NORMALIZER = ArxivNormalizer
