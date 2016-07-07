from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.mla'
    version = '0.0.1'
    title = 'mla'
    long_title = 'MLA Commons'
    home_page = 'https://commons.mla.org'
    url = 'https://commons.mla.org/deposits/oai/'
