from share.provider import ProviderAppConfig
from .harvester import HarvardDataverseHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.edu.harvarddataverse'
    version = '0.0.1'
    title = 'harvarddataverse'
    long_title = 'Harvard Dataverse'
    home_page = 'https://dataverse.harvard.edu'
    harvester = HarvardDataverseHarvester
