from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.erudit'
    version = '0.0.1'
    title = 'erudit'
    long_title = 'Érudit'
    home_page = 'http://erudit.org'
    url = 'http://oai.erudit.org/oai/request'
    disabled = True  # No longer has an OAI endpoint
