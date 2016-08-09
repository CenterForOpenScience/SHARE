from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.zenodo.oai'
    version = '0.0.1'
    title = 'zenodo'
    long_title = 'Zenodo'
    home_page = 'https://zenodo.org/oai2d'
    url = 'https://zenodo.org/oai2d'
