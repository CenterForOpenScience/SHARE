from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.boise_state'
    version = '0.0.1'
    title = 'boise_state'
    long_title = 'Boise State University ScholarWorks'
    home_page = 'http://scholarworks.boisestate.edu'
    url = 'http://scholarworks.boisestate.edu/do/oai/'
    property_list = [
        'source',
        'identifier',
        'type',
        'date',
        'setSpec',
        'publisher',
        'rights',
        'format',
    ]
