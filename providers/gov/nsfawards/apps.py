from share.provider import ProviderAppConfig
from .harvester import NSFAwardsHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.nsfawards'
    version = '0.0.1'
    title = 'nsfawards'
    rate_limit = (1, 3)
    long_title = 'NSF Awards'
    home_page = 'http://www.nsf.gov/'
    harvester = NSFAwardsHarvester
