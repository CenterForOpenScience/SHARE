from share import ProviderAppConfig
from .harvester import PLOSHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.plos'
    title = 'PLOS'
    long_title = 'Public Library of Science'
    home_page = 'https://plos.org/'
    harvester = PLOSHarvester
