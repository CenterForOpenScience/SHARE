from share import ProviderAppConfig

from providers.com.figshare.harvester import FigshareHarvester


class FigshareConfig(ProviderAppConfig):
    name = 'providers.com.figshare'

    title = 'figshare'
    harvester = FigshareHarvester
    home_page = 'https://figshare.com/'
