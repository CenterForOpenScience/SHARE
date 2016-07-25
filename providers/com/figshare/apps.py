from share import ProviderAppConfig
from .harvester import FigshareHarvester
from .normalizer import FigshareNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.com.figshare'
    version = '0.0.1'

    title = 'figshare'
    long_title = 'figshare'
    harvester = FigshareHarvester
    normalizer = FigshareNormalizer
    home_page = 'https://figshare.com/'
