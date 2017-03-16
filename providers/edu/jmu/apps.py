from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.jmu'
    version = '0.0.1'
    title = 'jmu'
    long_title = 'Scholarly Commons @ JMU'
    home_page = 'http://commons.lib.jmu.edu/'
    url = 'http://commons.lib.jmu.edu/do/oai/'
