from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.purdue'
    version = '0.0.1'
    title = 'purdue'
    long_title = 'PURR - Purdue University Research Repository'
    home_page = 'http://purr.purdue.edu'
    url = 'http://purr.purdue.edu/oaipmh'
    property_list = ['date', 'relation', 'identifier', 'type', 'setSpec']
