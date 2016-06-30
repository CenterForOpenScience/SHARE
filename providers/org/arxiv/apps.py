from share.provider import ProviderAppConfig
from .harvester import ArxivHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.arxiv'
    title = 'arxiv'
    long_title = 'ArXiv'
    home_page = 'https://arxiv.org'
    url = 'http://export.arxiv.org/api/query'
    time_granularity = False
    rate_limit = (1, 3)
    harvester = ArxivHarvester
    version = '0.0.0'
