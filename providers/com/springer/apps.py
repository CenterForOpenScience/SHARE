from share.provider import ProviderAppConfig
from .harvester import SpringerHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.springer'
    version = '0.0.1'
    title = 'springer'
    long_title = 'Springer | BioMed Central API'
    home_page = 'http://link.springer.com/'
    harvester = SpringerHarvester
