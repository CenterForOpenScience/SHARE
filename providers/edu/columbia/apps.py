from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.columbia'
    version = '0.0.1'
    title = 'columbia'
    long_title = 'Columbia Academic Commons'
    home_page = 'http://academiccommons.columbia.edu/'
    url = 'http://academiccommons.columbia.edu/catalog/oai'
