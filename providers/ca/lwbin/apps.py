from share.provider import ProviderAppConfig
from .harvester import LWBINHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.ca.lwbin'
    version = '0.0.1'
    title = 'lwbin'
    long_title = 'Lake Winnipeg Basin Information Network'
    home_page = 'http://130.179.67.140'
    harvester = LWBINHarvester
