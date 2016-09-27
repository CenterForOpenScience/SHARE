from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.wm'
    version = '0.0.1'
    title = 'w&m'
    long_title = 'College of William and Mary'
    home_page = 'http://publish.wm.edu/'
    url = 'http://publish.wm.edu/do/oai/'
    approved_sets = [
        'appliedsciencepub',
        'ckharrisdata',
        'ccrmresearchreports',
        'chsdreports',
        'ccrm',
        'chemistrypub',
        'chsd',
        'compmathstatspub',
        'computersciencepub',
        'dr',
        'geologypub',
        'internationalrelationspub',
        'linguisticspub',
        'mathematicspub',
        'neurosciencepub',
        'physicspub',
        'psychologypub',
        'researchtechnicalreports',
        'sociologypub',
        'spms',
        'samsroe',
        'ssr',
        'tsdpub',
        'ts',
        'yorkriverdata'
    ]
