from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.dryad'
    version = '0.0.1'
    title = 'dryad'
    long_title = 'Dryad Data Repository'
    home_page = 'http://www.datadryad.org/'
    url = 'http://www.datadryad.org/oai/request'
