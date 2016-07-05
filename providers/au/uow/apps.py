from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.au.uow'
    version = '0.0.1'
    title = 'uow'
    long_title = 'Research Online @ University of Wollongong'
    home_page = 'http://ro.uow.edu.au'
    url = 'http://ro.uow.edu.au/do/oai/'
    property_list = ['date', 'source', 'identifier', 'type', 'format', 'setSpec']
