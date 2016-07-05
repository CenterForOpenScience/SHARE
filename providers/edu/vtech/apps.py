from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.vtech'
    version = '0.0.1'
    title = 'vtech'
    long_title = 'Virginia Tech VTechWorks'
    home_page = 'https://vtechworks.lib.vt.edu'
    url = 'http://vtechworks.lib.vt.edu/oai/request'
    property_list = [
        'type',
        'source',
        'format',
        'date',
        'identifier',
        'setSpec',
        'rights',
        'relation',
    ]
