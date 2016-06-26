from share.provider import ProviderAppConfig
from .harvester import LWBINHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.edu.lwbin'
    title = 'lwbin'
    long_title = 'Lake Winnipeg Basin Information Network'
    home_page = 'http://130.179.67.140'
    harvester = LWBINHarvester
