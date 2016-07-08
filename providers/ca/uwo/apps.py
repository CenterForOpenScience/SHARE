from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.ca.uwo'
    version = '0.0.1'
    title = 'uwo'
    long_title = 'Western University'
    home_page = 'http://ir.lib.uwo.ca'
    url = 'http://ir.lib.uwo.ca/do/oai/'
