from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.scholarworks_umass'
    version = '0.0.1'
    title = 'scholarworks_umass'
    long_title = 'ScholarWorks@UMass Amherst'
    home_page = 'http://scholarworks.umass.edu'
    url = 'http://scholarworks.umass.edu/do/oai/'
    property_list = ['date', 'source', 'identifier', 'type', 'format']
