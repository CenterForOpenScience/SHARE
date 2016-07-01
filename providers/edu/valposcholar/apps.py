from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.valposcholar'
    version = '0.0.1'
    title = 'valposcholar'
    long_title = 'Valparaiso University ValpoScholar'
    home_page = 'http://scholar.valpo.edu/'
    url = 'http://scholar.valpo.edu/do/oai/'
