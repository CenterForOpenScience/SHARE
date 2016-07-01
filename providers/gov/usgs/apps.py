from share.provider import ProviderAppConfig
from .harvester import USGSHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.usgs'
    version = '0.0.1'
    title = 'usgs'
    long_title = 'United States Geological Survey'
    home_page = 'https://pubs.er.usgs.gov/'
    harvester = USGSHarvester
