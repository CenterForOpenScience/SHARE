from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.caltech'
    version = '0.0.1'
    title = 'caltech'
    long_title = 'CaltechAUTHORS'
    home_page = 'http://authors.library.caltech.edu/'
    url = 'http://authors.library.caltech.edu/cgi/oai2'
