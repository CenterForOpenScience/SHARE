from share.provider import ProviderAppConfig
from .harvester import CrossRefHarvester
from .normalizer import CrossRefNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.org.crossref'
    version = '0.0.1'
    title = 'crossref'
    long_title = 'CrossRef'
    home_page = 'http://www.crossref.org'
    harvester = CrossRefHarvester
    normalizer = CrossRefNormalizer
