from share.provider import ProviderAppConfig
from .harvester import NSFAwardsHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.nsfawards'
    title = 'nsfawards'
    long_title = 'NSF Awards'
    home_page = 'http://www.nsf.gov/'
    harvester = NSFAwardsHarvester
