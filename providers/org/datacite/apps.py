from share.provider import ProviderAppConfig
from .harvester import DataciteHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.org.datacite'
    version = '0.0.1'
    title = 'datacite'
    long_title = 'DataCite MDS'
    home_page = 'http://oai.datacite.org/'
    url = 'http://oai.datacite.org/oai'
    harvester = DataciteHarvester
