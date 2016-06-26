from share.provider import OAIProviderAppConfig


class BHLConfig(OAIProviderAppConfig):
    name = 'providers.org.arxiv'
    title = 'bhl'
    long_title = 'Biodiversity Heritage Library OAI Repository'
    home_page = 'http://www.biodiversitylibrary.org/'
    url = 'http://www.biodiversitylibrary.org/oai'
