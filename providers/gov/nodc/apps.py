from share.provider import ProviderAppConfig
from .harvester import NODCHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.nodc'
    version = '0.0.1'
    title = 'nodc'
    long_title = 'National Oceanographic Data Center'
    home_page = 'https://www.nodc.noaa.gov/'
    harvester = NODCHarvester
