from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.bhl'
    title = 'bhl'
    long_title = 'Biodiversity Heritage Library OAI Repository'
    home_page = 'http://www.biodiversitylibrary.org/'
    url = 'http://www.biodiversitylibrary.org/oai'
