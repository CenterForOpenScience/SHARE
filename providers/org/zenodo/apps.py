from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.zenodo'
    version = '0.0.1'
    title = 'zenodo'
    long_title = 'Zenodo'
    home_page = 'https://zenodo.org/oai2d'
    url = 'https://zenodo.org/oai2d'
    property_list = ['language', 'rights', 'source', 'relation', 'date', 'identifier', 'type']
