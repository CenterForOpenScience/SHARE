from share.provider import ProviderAppConfig
from .harvester import ELifeHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.elife'
    version = '0.0.1'
    title = 'elife'
    long_title = 'eLife Sciences'
    home_page = 'http://elifesciences.org/'
    harvester = ELifeHarvester
    rate_limit = (1, 60)
    namespaces = {
        'http://www.w3.org/1999/xlink': None,
        'http://www.w3.org/1998/Math/MathML': None,
    }
