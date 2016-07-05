from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.trinity'
    version = '0.0.1'
    title = 'trinity'
    long_title = 'Digital Commons @ Trinity University'
    home_page = 'http://digitalcommons.trinity.edu/'
    url = 'http://digitalcommons.trinity.edu/do/oai/'
    approved_sets = [
        'engine_faculty',
        'env_studocs',
        'geo_faculty',
        'geo_honors',
        'geo_studocs',
        'global-awareness',
        'hca_faculty',
        'hct_honors',
        'hist_faculty',
        'hist_honors',
        'infolit_qep',
        'infolit_usra',
        'lib_digitalcommons',
        'lib_docs',
        'lib_faculty',
        'math_faculty',
        'math_honors',
        'mll_faculty',
        'mll_honors',
        'mono',
        'music_honors',
        'oaweek',
        'phil_faculty',
        'phil_honors',
        'physics_faculty',
        'physics_honors',
        'polysci_faculty',
        'polysci_studocs',
        'psych_faculty',
        'psych_honors',
        'relig_faculty',
        'socanthro_faculty',
        'socanthro_honors',
        'socanthro_studocs',
        'speechdrama_honors',
        'urban_studocs',
        'written-communication',
    ]
    property_list = [
        'type',
        'format',
        'date',
        'identifier',
        'setSpec',
        'source',
        'coverage',
        'relation',
        'rights',
    ]
