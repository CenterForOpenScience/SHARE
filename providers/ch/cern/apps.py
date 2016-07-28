from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.ch.cern'
    version = '0.0.1'
    title = 'cern'
    long_title = 'CERN Document Server'
    home_page = 'http://cds.cern.ch'
    url = 'http://cdsweb.cern.ch/oai2d/'
