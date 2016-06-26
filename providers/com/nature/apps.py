from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.com.nature'
    title = 'nature'
    long_title = 'Nature Publishing Group'
    home_page =  'http://www.nature.com/'
    url = 'http://www.nature.com/oai/request'
    timezone_granularity = False
