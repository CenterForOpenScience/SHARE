from share.provider import ProviderAppConfig
from .harvester import BiomedCentralHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.biomedcentral'
    version = '0.0.1'
    title = 'biomedcentral'
    long_title = 'BioMed Central'
    home_page = 'http://www.springer.com/us/'
    harvester = BiomedCentralHarvester
    disabled = True  # Disabled as com.springer is the same api
