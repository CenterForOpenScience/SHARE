from share.provider import OAIProviderAppConfig

from providers.org.arxiv.harvester import ArxivHarvester


class ArxivConfig(OAIProviderAppConfig):
    name = 'providers.org.arxiv'
    label = 'org.arxiv'

    title = 'arxiv'
    harvester = ArxivHarvester
    home_page = 'https://arxiv.org'
