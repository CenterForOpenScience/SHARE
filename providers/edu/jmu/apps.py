from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.jmu'
    version = '0.0.1'
    title = 'jmu'
    long_title = 'James Madison University'
    home_page = 'http://commons.lib.jmu.edu/'
    url = 'http://commons.lib.jmu.edu/do/oai/'
    approved_sets = [
        'infrared',
        'acct',
        'sadah',
        'bio',
        'chembio',
        'csd',
        'commstudies',
        'cisba',
        'csci',
        'diss201019',
        'eere',
        'econ',
        'efae',
        'edspec201019',
        'engin',
        'eng',
        'finblaw',
        'fllc',
        'geoenv',
        'gradpsych',
        'celebrationofscholarship-grad',
        'hsci',
        'hist',
        'celebrationofscholarship-honors',
        'isat',
        'isat-ugrad',
        'intbus',
        'jmurj',
        'justice',
        'kine',
        'ltle',
        'lexia',
        'letfspubs',
        'madrush',
        'mhr',
        'madisonmagazine',
        'mgmt',
        'mktg',
        'master201019',
        'mathstat',
        'smad',
        'mecmsrps',
        'msme',
        'milsci',
        'music',
        'nursing',
        'phrel',
        'paa',
        'polisci',
        'psyc',
        'scomconference',
        'photon',
        'honors201019',
        'socwrk',
        'socant',
        'theadan',
        'wrtc'
    ]
