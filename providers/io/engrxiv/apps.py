from share.provider import ProviderAppConfig
from .harvester import EngrxivHarvester
from .normalizer import EngrxivNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.io.engrxiv'
    version = '0.0.1'
    title = 'osf'
    long_title = 'Socarxiv'
    home_page = 'http://osf.io/api/v1/search/'
    emitted_type = 'preprint'
    harvester = EngrxivHarvester
    normalizer = EngrxivNormalizer
