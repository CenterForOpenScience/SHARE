from share import ProviderAppConfig
from .harvester import FigshareHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.figshare'

    title = 'figshare'
    long_title = 'figshare'
    harvester = FigshareHarvester
    home_page = 'https://figshare.com/'
