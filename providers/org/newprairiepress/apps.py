from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.newprairiepress'
    version = '0.0.1'
    title = 'newprairiepress'
    long_title = 'New Prairie Press at Kansas State University'
    home_page = 'http://newprairiepress.org'
    url = 'http://newprairiepress.org/do/oai/'
    property_list = ['identifier', 'source', 'date', 'type', 'format', 'setSpec']
