from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.krex'
    version = '0.0.1'
    title = 'krex'
    long_title = 'K-State Research Exchange'
    home_page = 'http://krex.k-state.edu'
    url = 'http://krex.k-state.edu/dspace-oai/request'
