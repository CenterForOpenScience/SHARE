from share.provider import OAIProviderAppConfig
from .harvester import GhentHarvester


class CogPrintsConfig(OAIProviderAppConfig):
    name = 'providers.be.ghent'

    title = 'ghent'
    long_title = 'Ghent University Academic Bibliography'
    harvester = GhentHarvester
    home_page = 'https://biblio.ugent.be/'
