from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.uky'
    version = '0.0.1'
    title = 'uky'
    long_title = 'UKnowledge @ University of Kentucky'
    home_page = 'http://uknowledge.uky.edu'
    url = 'http://uknowledge.uky.edu/do/oai/'
    property_list = ['date', 'source', 'identifier', 'type', 'format', 'setSpec']
