from share.provider import ProviderAppConfig
from .harvester import BiomedCentralHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.biomedcentral'
    title = 'biomedcentral'
    long_title = 'BioMed Central'
    home_page = 'http://www.springer.com/us/'
    harvester = BiomedCentralHarvester
