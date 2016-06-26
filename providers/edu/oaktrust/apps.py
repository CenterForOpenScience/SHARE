from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.oaktrust'
    title = 'oaktrust'
    long_title = 'The OAKTrust Digital Repository at Texas A&M'
    home_page = 'http://oaktrust.library.tamu.edu'
    url = 'http://oaktrust.library.tamu.edu/dspace-oai/request'
