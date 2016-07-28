from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.eu.econstor'
    version = '0.0.1'
    title = 'econstor'
    long_title = 'EconStor'
    home_page = 'http://www.econstor.eu/dspace/'
    url = 'http://www.econstor.eu/dspace-oai/request'
