from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.duke'
    version = '0.0.1'
    title = 'duke'
    long_title = 'Duke University Libraries'
    home_page = 'http://dukespace.lib.duke.edu'
    url = 'http://dukespace.lib.duke.edu/dspace-oai/request'
