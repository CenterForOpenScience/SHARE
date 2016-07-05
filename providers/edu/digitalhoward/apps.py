from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.digitalhoward'
    version = '0.0.1'
    title = 'digitalhoward'
    long_title = 'Digital Howard @ Howard University'
    home_page = 'http://dh.howard.edu'
    url = 'http://dh.howard.edu/do/oai/'
    property_list = ['date', 'source', 'identifier', 'type', 'rights']
