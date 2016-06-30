from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.colostate'
    version = '0.0.1'
    title = 'colostate'
    long_title = 'Digital Collections of Colorado'
    home_page = 'https://dspace.library.colostate.edu'
    url = 'https://dspace.library.colostate.edu/oai/request'
