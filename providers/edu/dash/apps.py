from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.dash'
    title = 'dash'
    long_title = 'Digital Access to Scholarship at Harvard'
    home_page = 'http://dash.harvard.edu'
    url = 'http://dash.harvard.edu/oai/request'
