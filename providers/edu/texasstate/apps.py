from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.texasstate'
    version = '0.0.1'
    title = 'texasstate'
    long_title = 'DSpace at Texas State University'
    home_page = 'https://digital.library.txstate.edu/'
    url = 'http://digital.library.txstate.edu/oai/request'
