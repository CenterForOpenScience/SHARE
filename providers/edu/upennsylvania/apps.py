from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.upennsylvania'
    version = '0.0.1'
    title = 'upennsylvania'
    long_title = 'University of Pennsylvania Scholarly Commons'
    home_page = 'http://repository.upenn.edu'
    url = 'http://repository.upenn.edu/do/oai/'
    property_list = ['type', 'format', 'date', 'identifier', 'setSpec', 'source', 'rights']
