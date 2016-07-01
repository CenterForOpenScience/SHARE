from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.umich'
    version = '0.0.1'
    title = 'umich'
    long_title = 'Deep Blue @ University of Michigan'
    home_page = 'http://deepblue.lib.umich.edu'
    url = 'http://deepblue.lib.umich.edu/dspace-oai/request'
