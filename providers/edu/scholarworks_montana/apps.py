from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.scholarworks_montana'
    version = '0.0.1'
    title = 'scholarworks_montana'
    long_title = 'Montana State University'
    home_page = 'http://scholarworks.montana.edu'
    url = 'http://scholarworks.montana.edu/oai/request'
