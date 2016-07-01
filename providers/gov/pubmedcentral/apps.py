from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.gov.pubmedcentral'
    version = '0.0.1'
    title = 'pubmedcentral'
    long_title = 'PubMed Central'
    home_page = 'http://www.ncbi.nlm.nih.gov/pmc/'
    url = 'http://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi'
