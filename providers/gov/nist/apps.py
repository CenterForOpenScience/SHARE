from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.gov.nist'
    version = '0.0.1'
    title = 'nist'
    long_title = 'NIST MaterialsData'
    home_page = 'https://materialsdata.nist.gov'
    url = 'https://materialsdata.nist.gov/dspace/oai/request'
