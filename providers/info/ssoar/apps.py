from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.info.ssoar'
    version = '0.0.1'
    title = 'ssoar'
    long_title = 'Social Science Open Access Repository'
    home_page = 'http://www.ssoar.info/en/home.html'
    url = 'http://www.ssoar.info/OAIHandler/request'
    # http://www.ssoar.info/ssoar/search-filter?field=documentType
    type_map = {
        'journal article': 'article',
        'festschrift': 'publication',
        'final report': 'report',
        'company report': 'report',
        'research report': 'report',
        'expert report': 'report',
        'abridged report': 'report',
        'literature report': 'report',
        'annual report': 'report',
        'interim report': 'report',
        'report from institution/organization': 'report',
        'm.a. thesis': 'thesis',
        'master thesis': 'thesis',
        'phd thesis': 'thesis',
        'conference paper': 'conferencepaper',
        'working paper': 'workingpaper',
        'other': 'creativework'
    }
