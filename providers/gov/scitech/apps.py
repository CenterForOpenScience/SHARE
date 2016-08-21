from share.provider import ProviderAppConfig
from .harvester import SciTechHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.scitech'
    version = '0.0.1'
    title = 'scitech'
    long_title = 'DoE\'s SciTech Connect Database'
    home_page = 'http://www.osti.gov/scitech'
    harvester = SciTechHarvester

    namespaces = {
        'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf',
        'http://purl.org/dc/elements/1.1/': 'dc',
        'http://purl.org/dc/terms/': 'dcq',
    }
