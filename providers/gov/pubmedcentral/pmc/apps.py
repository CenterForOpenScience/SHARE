from share.provider import ProviderAppConfig
from .harvester import PMCHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.gov.pubmedcentral.pmc'
    version = '0.0.1'
    title = 'pmc-metadata'
    long_title = 'PubMed Central: PMC Metadata'
    home_page = 'http://www.ncbi.nlm.nih.gov/pmc/'
    url = 'https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi'
    time_granularity = False
    harvester = PMCHarvester
    namespaces = {
        'http://www.openarchives.org/OAI/2.0/': None,
        'http://jats.nlm.nih.gov/ns/archiving/1.0/': None,
        'http://www.w3.org/2001/XMLSchema-instance': 'xsi',
        'http://www.niso.org/schemas/ali/1.0': 'ali',
        'http://www.w3.org/1999/xlink': 'xlink',
        'http://www.w3.org/1998/Math/MathML': 'mml'
    }
