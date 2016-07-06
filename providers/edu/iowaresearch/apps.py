from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.iowaresearch'
    version = '0.0.1'
    title = 'iowaresearch'
    long_title = 'Iowa Research Online'
    home_page = 'http://ir.uiowa.edu'
    url = 'http://ir.uiowa.edu/do/oai/'
    property_list = []
