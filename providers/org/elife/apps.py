from share.provider import ProviderAppConfig
from share.normalize.soup import SoupXMLNormalizer

from .harvester import ELifeHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.elife'
    version = '0.0.1'
    title = 'elife'
    long_title = 'eLife Sciences'
    home_page = 'http://elifesciences.org/'
    harvester = ELifeHarvester
    normalizer = SoupXMLNormalizer
