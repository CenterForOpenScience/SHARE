from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.ucescholarship'
    version = '0.0.1'
    title = 'ucescholarship'
    long_title = 'eScholarship @ University of California'
    home_page = 'http://www.escholarship.org/'
    url = 'http://www.escholarship.org/uc/oai'
