from share.provider import ProviderAppConfig
from .harvester import HarvardDataverseHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.edu.harvarddataverse'
    title = 'harvarddataverse'
    long_title = 'Harvard Dataverse'
    home_page = 'https://dataverse.harvard.edu'
    harvester = HarvardDataverseHarvester
