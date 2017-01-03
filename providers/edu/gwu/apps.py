from share.provider import ProviderAppConfig
from .harvester import GWScholarSpaceHarvester
from .normalizer import GWScholarSpaceNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.edu.gwu'
    version = '0.0.0'
    title = 'gwu'
    long_title = 'ScholarSpace @ George Washington University'
    home_page = 'https://scholarspace.library.gwu.edu'
    url = 'https://scholarspace.library.gwu.edu/catalog'
    harvester = GWScholarSpaceHarvester
    normalizer = GWScholarSpaceNormalizer
