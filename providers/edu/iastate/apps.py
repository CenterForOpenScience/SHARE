from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.iastate'
    version = '0.0.1'
    title = 'iastate'
    long_title = 'Digital Repository @ Iowa State University'
    home_page = 'http://lib.dr.iastate.edu'
    url = 'http://lib.dr.iastate.edu/do/oai/'
