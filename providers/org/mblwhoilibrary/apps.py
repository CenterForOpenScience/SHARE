from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.mblwhoilibrary'
    version = '0.0.1'
    title = 'mblwhoilibrary'
    long_title = 'WHOAS at MBLWHOI Library'
    home_page = 'http://darchive.mblwhoilibrary.org'
    url = 'http://darchive.mblwhoilibrary.org/oai/request'
    property_list = ['date', 'relation', 'identifier', 'type', 'format', 'setSpec']
