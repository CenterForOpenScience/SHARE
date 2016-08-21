from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.ru.cyberleninka'
    version = '0.0.1'
    title = 'cyberleninka'
    long_title = 'CyberLeninka - Russian open access scientific library'
    home_page = 'http://cyberleninka.ru/'
    url = 'http://cyberleninka.ru/oai'
    # using a subset of terms from the dcterms namespace
    property_list = [
        'isPartOf',
        'issue',
        'issn',
        'pages',
        'bibliographicCitation',
        'uri'
    ]
