from share.provider import ProviderAppConfig
from .harvester import DataOneHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.dataone'
    version = '0.0.1'
    title = 'dataone'
    long_title = 'DataONE: Data Observation Network for Earth'
    home_page = 'https://www.dataone.org/'
    harvester = DataOneHarvester
