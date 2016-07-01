from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.wustlopenscholarship'
    version = '0.0.1'
    title = 'wustlopenscholarship'
    long_title = 'Washington University Open Scholarship'
    home_page = 'http://openscholarship.wustl.edu'
    url = 'http://openscholarship.wustl.edu/do/oai/'
