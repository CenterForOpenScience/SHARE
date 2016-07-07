from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.asu'
    version = '0.0.1'
    title = 'asu'
    long_title = 'Arizona State University Digital Repository'
    home_page = 'http://www.asu.edu/'
    url = 'http://repository.asu.edu/oai-pmh'
    approved_sets = ['research']
