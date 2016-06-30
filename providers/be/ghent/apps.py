from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.be.ghent'
    version = '0.0.1'
    title = 'ghent'
    long_title = 'Ghent University Academic Bibliography'
    home_page = 'https://biblio.ugent.be/'
    url = 'https://biblio.ugent.be/oai'
