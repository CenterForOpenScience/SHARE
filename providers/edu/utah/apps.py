from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.utah'
    version = '0.0.1'
    title = 'utah'
    long_title = 'University of Utah'
    home_page = 'http://lib.utah.edu/'
    url = 'https://collections.lib.utah.edu/oai'
    approved_sets = ['ir_uspace']
    time_granularity = False
