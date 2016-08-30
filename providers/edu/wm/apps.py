from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.wm'
    version = '0.0.1'
    title = 'w&m'
    long_title = 'College of William and Mary'
    home_page = 'http://publish.wm.edu/'
    url = 'http://publish.wm.edu/do/oai/'
    approved_sets = [
        u'appliedsciencepub',
        u'ckharrisdata',
        u'ccrmresearchreports',
        u'chsdreports',
        u'ccrm',
        u'chemistrypub',
        u'chsd',
        u'compmathstatspub',
        u'computersciencepub',
        u'dr',
        u'geologypub',
        u'internationalrelationspub',
        u'linguisticspub',
        u'mathematicspub',
        u'neurosciencepub',
        u'physicspub',
        u'psychologypub',
        u'researchtechnicalreports',
        u'sociologypub',
        u'spms',
        u'samsroe',
        u'ssr',
        u'tsdpub',
        u'ts',
        u'yorkriverdata'
    ]
