from share.provider import OAIProviderAppConfig
from .harvester import PMCHarvester


class AppConfig(OAIProviderAppConfig):
    name = 'providers.gov.pubmedcentral.pmc'
    version = '0.0.1'
    title = 'pmc-metadata'
    long_title = 'PubMed Central: PMC Metadata'
    home_page = 'http://www.ncbi.nlm.nih.gov/pmc/'
    url = 'https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi'
    time_granularity = False
    harvester = PMCHarvester
