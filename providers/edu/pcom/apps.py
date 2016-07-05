from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.pcom'
    version = '0.0.1'
    title = 'pcom'
    long_title = 'DigitalCommons@PCOM'
    home_page = 'http://digitalcommons.pcom.edu'
    url = 'http://digitalcommons.pcom.edu/do/oai/'
    approved_sets = [
        'biomed',
        'pa_systematic_reviews',
        'psychology_dissertations',
        'scholarly_papers',
        'research_day',
        'posters',
    ]
    property_list = ['date', 'source', 'identifier', 'type', 'format', 'setSpec']
