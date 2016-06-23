from share.provider import OAIProviderAppConfig
from .harvester import CambridgeHarvester


class CambridgeConfig(OAIProviderAppConfig):
    name = 'providers.uk.ac.cambridge'

    title = 'cambridge'
    long_title = 'Apollo @ University of Cambridge'
    harvester = CambridgeHarvester
    home_page = 'https://www.repository.cam.ac.uk'
