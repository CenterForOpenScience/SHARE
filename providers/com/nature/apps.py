from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.com.nature'
    version = '0.0.1'
    title = 'nature'
    long_title = 'Nature Publishing Group'
    home_page = 'http://www.nature.com/'
    url = 'http://www.nature.com/oai/request'
    time_granularity = False
    emitted_type = 'publication'
