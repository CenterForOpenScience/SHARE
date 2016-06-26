from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.citeseerx'
    title = 'citeseerx'
    long_title = 'CiteSeerX Scientific Literature Digital Library and Search Engine'
    home_page = 'http://citeseerx.ist.psu.edu'
    url = 'http://citeseerx.ist.psu.edu/oai2'
    timezone_granularity = False
