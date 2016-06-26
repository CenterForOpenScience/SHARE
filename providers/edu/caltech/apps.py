from share.provider import OAIProviderAppConfig


class CaltechConfig(OAIProviderAppConfig):
    name = 'providers.edu.caltech'
    title = 'caltech'
    long_title = 'CaltechAUTHORS'
    home_page = 'http://authors.library.caltech.edu/'
    url = 'http://authors.library.caltech.edu/cgi/oai2'
