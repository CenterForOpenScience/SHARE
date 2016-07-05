from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.wash_state_u'
    version = '0.0.1'
    title = 'wash_state_u'
    long_title = 'Washington State University Research Exchange'
    home_page = 'http://research.wsulibs.wsu.edu/xmlui/'
    url = 'http://research.wsulibs.wsu.edu:8080/oai/request'
    property_list = ['identifier', 'date', 'format', 'type', 'setSpec']
