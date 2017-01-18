from share.provider import ProviderAppConfig
from .harvester import AgEconHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.edu.ageconsearch'
    version = '0.0.1'
    title = 'agecon'
    long_title = 'AgEcon Search'
    home_page = 'http://ageconsearch.umn.edu/'
    harvester = AgEconHarvester
