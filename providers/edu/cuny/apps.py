from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.cuny'
    version = '0.0.1'
    title = 'cuny'
    long_title = 'City University of New York'
    home_page = 'http://academicworks.cuny.edu'
    url = 'http://academicworks.cuny.edu/do/oai/'
