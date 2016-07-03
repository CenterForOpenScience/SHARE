from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.bhl'
    version = '0.0.1'
    title = 'bhl'
    long_title = 'Biodiversity Heritage Library OAI Repository'
    home_page = 'http://www.biodiversitylibrary.org/'
    url = 'http://www.biodiversitylibrary.org/oai'
    time_granularity = False
