from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.mason'
    version = '0.0.1'
    title = 'mason'
    long_title = 'Mason Archival Repository Service'
    home_page = 'http://mars.gmu.edu/'
    url = 'http://mars.gmu.edu/oai/request'
