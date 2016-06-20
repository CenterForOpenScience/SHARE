from share.core import ProviderAppConfig


class FigshareConfig(ProviderAppConfig):
    name = 'providers.com.figshare'

    title = 'figshare'
    home_page = 'https://figshare.com/'

    @property
    def harvester(self):
        from .harvester import FigshareHarvester
        return FigshareHarvester
