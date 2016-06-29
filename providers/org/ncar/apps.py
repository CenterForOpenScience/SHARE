from share.provider import ProviderAppConfig
from .harvester import NCARHarvester

class AppConfig(ProviderAppConfig):
    name = 'providers.org.ncar'
    version = '0.0.1'
    title = 'ncar'
    long_title = 'Earth System Grid at NCAR'
    home_page = 'https://www.earthsystemgrid.org/'
    harvester = NCARHarvester
