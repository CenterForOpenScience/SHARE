from share.provider import ProviderAppConfig
from .harvester import ResearchRegistryHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.researchregistry'
    version = '0.0.0'
    title = 'Research Registry'
    long_title = 'Research Registry'
    home_page = 'http://www.researchregistry.com/'
    harvester = ResearchRegistryHarvester
