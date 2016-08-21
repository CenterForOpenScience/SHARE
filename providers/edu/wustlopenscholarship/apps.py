from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.wustlopenscholarship'
    version = '0.0.1'
    title = 'wustlopenscholarship'
    long_title = 'Washington University Open Scholarship'
    home_page = 'http://openscholarship.wustl.edu'
    url = 'http://openscholarship.wustl.edu/do/oai/'
    approved_sets = [
        'cse_research',
        'facpubs',
        'art_sci_facpubs',
        'lib_research',
        'artarch_facpubs',
        'bio_facpubs',
        'brown_facpubs',
        'cfh_facpubs',
        'engl_facpubs',
        'hist_facpubs',
        'math_facpubs',
        'psych_facpubs',
        'lib_present',
        'lib_papers',
        'wgssprogram',
    ]
