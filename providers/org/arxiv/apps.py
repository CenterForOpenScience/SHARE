from share.provider import ProviderAppConfig
from .harvester import ArxivHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.arxiv'
    title = 'arxiv'
    long_title = 'ArXiv'
    home_page = 'https://arxiv.org'
    url = 'http://export.arxiv.org/api/query?search_query=all'
    time_granularity = False
    harvester = ArxivHarvester
