from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.umassmed'
    version = '0.0.1'
    title = 'umassmed'
    long_title = 'eScholarship@UMMS'
    home_page = 'http://escholarship.umassmed.edu'
    url = 'http://escholarship.umassmed.edu/do/oai/'
