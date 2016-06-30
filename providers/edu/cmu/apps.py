from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.cmu'
    version = '0.0.1'
    title = 'cmu'
    long_title = 'Carnegie Mellon University Research Showcase'
    home_page = 'http://repository.cmu.edu/'
    url = 'http://repository.cmu.edu/do/oai/'
