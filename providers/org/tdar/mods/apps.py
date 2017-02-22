from share.provider import MODSProviderAppConfig


class AppConfig(MODSProviderAppConfig):
    name = 'providers.org.tdar.mods'
    version = '0.0.1'
    title = 'tdar'
    long_title = 'The Digital Archaeological Record'
    home_page = 'http://www.tdar.org'
    url = 'http://core.tdar.org/oai-pmh/oai'
