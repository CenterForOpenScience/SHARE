from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.ukansas'
    version = '0.0.1'
    title = 'ukansas'
    long_title = 'KU ScholarWorks'
    home_page = 'https://kuscholarworks.ku.edu'
    url = 'https://kuscholarworks.ku.edu/oai/request'
    property_list = ['date', 'identifier', 'type', 'format', 'setSpec']
