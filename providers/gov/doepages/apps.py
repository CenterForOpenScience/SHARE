from share.provider import ProviderAppConfig
from .harvester import DoepagesHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.doepages'
    title = 'doepages'
    long_title = 'Department of Energy Pages'
    home_page = 'http://www.osti.gov/pages/'
    harvester = DoepagesHarvester
