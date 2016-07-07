from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.ut_chattanooga'
    version = '0.0.1'
    title = 'ut_chattanooga'
    long_title = 'University of Tennessee at Chattanooga'
    home_page = 'http://scholar.utc.edu'
    url = 'http://scholar.utc.edu/do/oai/'
    approved_sets = ['honors-theses', 'theses']
