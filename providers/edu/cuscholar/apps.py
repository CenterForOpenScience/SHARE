from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.cuscholar'
    title = 'cuscholar'
    long_title = 'CU Scholar University of Colorado Boulder'
    home_page = 'http://scholar.colorado.edu'
    url = 'http://scholar.colorado.edu/do/oai/'
