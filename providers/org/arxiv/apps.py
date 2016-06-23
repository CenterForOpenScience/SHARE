from share.provider import OAIProviderAppConfig
from .harvester import ArxivHarvester


class ArxivConfig(OAIProviderAppConfig):
    name = 'providers.org.arxiv'

    title = 'arxiv'
    long_title = 'ArXiv'
    harvester = ArxivHarvester
    home_page = 'https://arxiv.org'
