from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.kent'
    version = '0.0.1'
    title = 'kent'
    long_title = 'Digital Commons @ Kent State University Libraries'
    home_page = 'http://digitalcommons.kent.edu'
    url = 'http://digitalcommons.kent.edu/do/oai/'
    property_list = []
