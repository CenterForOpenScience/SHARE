from share.provider import ProviderAppConfig
from .harvester import NCARHarvester

class AppConfig(ProviderAppConfig):
    name = 'providers.org.ncar'
    title = 'ncar'
    long_title = 'Earth System Grid at NCAR'
    home_page = 'https://www.earthsystemgrid.org/'
    harvester = NCARHarvester
