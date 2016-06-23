from share import ProviderAppConfig
from .harvester import FigshareHarvester


class FigshareConfig(ProviderAppConfig):
    name = 'providers.com.figshare'

    title = 'figshare'
    long_title = 'figshare'
    harvester = FigshareHarvester
    home_page = 'https://figshare.com/'
