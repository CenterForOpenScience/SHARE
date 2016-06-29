from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.fit'
    version = '0.0.1'
    title = 'fit'
    long_title = 'Florida Institute of Technology'
    home_page = 'http://repository.lib.fit.edu'
    url = 'http://repository.lib.fit.edu/oai/request'
