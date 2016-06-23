from share.provider import OAIProviderAppConfig
from .harvester import CogPrintsHarvester


class CogPrintsConfig(OAIProviderAppConfig):
    name = 'providers.org.cogprints'

    title = 'cogprints'
    long_title = 'Cognitive Sciences ePrint Archive'
    harvester = CogPrintsHarvester
    home_page = 'http://www.cogprints.org/'
