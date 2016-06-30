from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.dash'
    version = '0.0.1'
    title = 'dash'
    long_title = 'Digital Access to Scholarship at Harvard'
    home_page = 'http://dash.harvard.edu'
    url = 'http://dash.harvard.edu/oai/request'
