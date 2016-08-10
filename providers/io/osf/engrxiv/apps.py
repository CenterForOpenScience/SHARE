from share.provider import ProviderAppConfig
from .harvester import EngrxivHarvester
from provider.io.osf.normalizer import OSFNormalizer

class AppConfig(ProviderAppConfig):
    name = 'providers.io.osf.engrxiv'
    version = '0.0.1'
    title = 'osf'
    long_title = 'Socarxiv'
    home_page = 'http://osf.io/api/v1/search/'
    harvester = EngrxivHarvester
    normalizer = OSFNormalizer
