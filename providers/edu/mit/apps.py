from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.mit'
    version = '0.0.1'
    title = 'mit'
    long_title = 'DSpace@MIT'
    home_page = 'http://dspace.mit.edu/'
    url = 'http://dspace.mit.edu/oai/request'
