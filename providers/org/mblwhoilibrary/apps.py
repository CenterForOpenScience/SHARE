from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.mblwhoilibrary'
    title = 'mblwhoilibrary'
    long_title = 'WHOAS at MBLWHOI Library'
    home_page = 'http://darchive.mblwhoilibrary.org'
    url = 'http://darchive.mblwhoilibrary.org/oai/request'
