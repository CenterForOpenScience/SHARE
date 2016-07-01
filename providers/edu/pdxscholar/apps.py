from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.pdxscholar'
    version = '0.0.1'
    title = 'pdxscholar'
    long_title = 'PDXScholar Portland State University'
    home_page = 'http://pdxscholar.library.pdx.edu'
    url = 'http://pdxscholar.library.pdx.edu/do/oai/'
