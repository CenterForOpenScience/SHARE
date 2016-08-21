from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.smithsonian'
    version = '0.0.1'
    title = 'smithsonian'
    long_title = 'Smithsonian Digital Repository'
    home_page = 'http://repository.si.edu'
    url = 'http://repository.si.edu/oai/request'
