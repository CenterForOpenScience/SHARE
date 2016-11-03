from share.provider import ProviderAppConfig
from .harvester import NCARHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.ncar'
    version = '0.0.1'
    title = 'ncar'
    long_title = 'Earth System Grid at NCAR'
    home_page = 'http://www.earthsystemgrid.org/'
    harvester = NCARHarvester
    url = 'https://www.earthsystemgrid.org/oai/'
    namespaces = {
        'http://gcmd.gsfc.nasa.gov/Aboutus/xml/dif/': None,
        'http://www.openarchives.org/OAI/2.0/': None
    }
