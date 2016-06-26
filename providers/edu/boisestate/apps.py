from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.boisestate'
    title = 'boisestate'
    long_title = 'Boise State University ScholarWorks'
    home_page = 'http://scholarworks.boisestate.edu'
    url = 'http://scholarworks.boisestate.edu/do/oai/'
