from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.ru.cyberleninka'
    version = '0.0.1'
    title = 'cyberleninka'
    long_title = 'CyberLeninka - Russian open access scientific library'
    home_page = 'http://cyberleninka.ru/'
    url = 'http://cyberleninka.ru/oai'
    property_list = [
        'isPartOf',
        'type',
        'format',
        'issue',
        'issn',
        'pages',
        'bibliographicCitation',
        'uri',
        'date',
        'identifier',
        'type',
    ]
