from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.utaustin'
    version = '0.0.1'
    title = 'utaustin'
    long_title = 'University of Texas at Austin Digital Repository'
    home_page = 'https://repositories.lib.utexas.edu'
    url = 'https://repositories.lib.utexas.edu/utexas-oai/request'
