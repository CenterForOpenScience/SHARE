from share.provider import ProviderAppConfig
from .harvester import VIVOHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.edu.vivo'
    version = '0.0.1'
    title = 'vivo'
    long_title = 'VIVO'
    home_page = 'http://dev.vivo.ufl.edu/'
    harvester = VIVOHarvester
