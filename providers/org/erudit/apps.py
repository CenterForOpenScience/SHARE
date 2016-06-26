from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.erudit'
    title = 'erudit'
    long_title = 'Érudit'
    home_page = 'http://erudit.org'
    url = 'http://oai.erudit.org/oai/request'
