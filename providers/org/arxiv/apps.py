from share.provider import ProviderAppConfig
from .harvester import ArxivHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.arxiv'
    version = '0.0.1'
    title = 'arxiv'
    long_title = 'ArXiv'
    home_page = 'http://arxiv.org'
    url = 'http://export.arxiv.org/api/query'
    time_granularity = False
    rate_limit = (1, 3)
    harvester = ArxivHarvester

    namespaces = {
        'http://www.w3.org/2005/Atom': None,
        'http://arxiv.org/schemas/atom': 'arxiv',
    }
