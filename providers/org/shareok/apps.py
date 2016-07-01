from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.shareok'
    version = '0.0.1'
    title = 'shareok'
    long_title = 'SHAREOK Repository'
    home_page = 'https://shareok.org'
    url = 'https://shareok.org/oai/request'
