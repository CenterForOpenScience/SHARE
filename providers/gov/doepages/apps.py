from share.provider import ProviderAppConfig
from .harvester import DoepagesHarvester
from .normalizer import DoepagesNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.doepages'
    version = '0.0.1'
    title = 'doepages'
    long_title = 'Department of Energy Pages'
    home_page = 'http://www.osti.gov/pages/'
    harvester = DoepagesHarvester
    normalizer = DoepagesNormalizer
