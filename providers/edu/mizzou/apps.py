from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.mizzou'
    version = '0.0.1'
    title = 'mizzou'
    long_title = 'MOspace Institutional Repository'
    home_page = 'https://mospace.umsystem.edu'
    url = 'https://mospace.umsystem.edu/oai/request'
