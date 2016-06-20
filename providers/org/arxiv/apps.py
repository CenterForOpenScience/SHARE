from share.core import OAIProviderAppConfig


class ArxivConfig(OAIProviderAppConfig):
    name = 'providers.org.arxiv'

    title = 'arxiv'
    home_page = ''

    @property
    def harvester(self):
        from .harvester import ArxivHarvester
        return ArxivHarvester
