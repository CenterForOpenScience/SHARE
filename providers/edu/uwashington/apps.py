from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.uwashington'
    version = '0.0.1'
    title = 'uwashington'
    long_title = 'ResearchWorks @ University of Washington'
    home_page = 'https://digital.lib.washington.edu/'
    url = 'http://digital.lib.washington.edu/dspace-oai/request'
    property_list = ['type', 'source', 'format', 'date', 'identifier', 'setSpec', 'rights']
