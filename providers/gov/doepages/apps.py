import providers.gov.scitech.normalizer as SciTechParser
from share.provider import ProviderAppConfig
from .harvester import DoepagesHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.doepages'
    version = '0.0.1'
    title = 'doepages'
    long_title = 'Department of Energy Pages'
    home_page = 'http://www.osti.gov/pages/'
    harvester = DoepagesHarvester
    # Use the SciTech Parser since DOEPages follows the same schema
    root_parser = SciTechParser.CreativeWork
