from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.sldr'
    version = '0.0.1'
    title = 'sldr'
    long_title = 'Speech and Language Data Repository (SLDR/ORTOLANG)'
    home_page = 'http://sldr.org'
    url = 'http://sldr.org/oai-pmh.php'
    time_granularity = False
    approved_sets = [
        'publisher',
        'date',
        'language',
        'rights',
        'license',
        'format',
        'isPartOf',
        'created',
        'accessRights',
        'temporal',
        'source',
        'bibliographicCitation',
        'modified',
        'spatial',
        'requires',
        'identifier',
        'type',
        'tableOfContents',
        'ortolang',
        'archive:long-term',
    ]
    # using a subset of terms from the dcterms namespace
    property_list = [
        'modified',
        'temporal',
        'extent',
        'spatial',
        'abstract',
        'created',
        'license',
        'bibliographicCitation',
        'isPartOf',
        'tableOfContents',
        'accessRights'
    ]
