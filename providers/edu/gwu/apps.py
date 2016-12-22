from share.provider import ProviderAppConfig
from .harvester import GWScholarSpaceHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.edu.gwu'
    version = '0.0.0'
    title = 'gwu'
    long_title = 'ScholarSpace @ George Washington University'
    home_page = 'https://scholarspace.library.gwu.edu'
    #rate_limit = (1, 5) TODO is there a rate limit?
    url = 'https://scholarspace.library.gwu.edu/catalog'
    harvester = GWScholarSpaceHarvester
