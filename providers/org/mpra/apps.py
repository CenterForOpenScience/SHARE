from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.mpra'
    version = '0.0.1'
    title = 'mpra'
    long_title = 'Munich Personal RePEc Archive'
    home_page = 'http://mpra.ub.uni-muenchen.de'
    url = 'http://mpra.ub.uni-muenchen.de/perl/oai2'