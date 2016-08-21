from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.tdar'
    version = '0.0.1'
    title = 'tdar'
    long_title = 'The Digital Archaeological Record'
    home_page = 'http://www.tdar.org'
    url = 'http://core.tdar.org/oai-pmh/oai'
