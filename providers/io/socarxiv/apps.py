from share.provider import ProviderAppConfig
from .harvester import SocarxivHarvester
from .normalizer import SocarxivNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.io.socarxiv'
    version = '0.0.1'
    title = 'osf'
    long_title = 'Socarxiv'
    emitted_type = 'preprint'
    home_page = 'http://osf.io/api/v1/search/'
    harvester = SocarxivHarvester
    normalizer = SocarxivNormalizer
