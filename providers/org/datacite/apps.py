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
    namespaces = {
        'http://purl.org/dc/elements/1.1/': 'dc',
        'http://datacite.org/schema/kernel-3': None,
        'http://www.openarchives.org/OAI/2.0/': None,
        'http://schema.datacite.org/oai/oai-1.0/': None,
        'http://www.openarchives.org/OAI/2.0/oai_dc/': None,
    }
