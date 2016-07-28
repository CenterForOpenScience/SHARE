from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.datacite.oai'
    version = '0.0.1'
    title = 'datacite'
    long_title = 'DataCite MDS'
    home_page = 'http://oai.datacite.org/'
    url = 'http://oai.datacite.org/oai'
