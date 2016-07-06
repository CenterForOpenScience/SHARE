from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.huskiecommons'
    version = '0.0.1'
    title = 'huskiecommons'
    long_title = 'Huskie Commons @ Northern Illinois University'
    home_page = 'http://commons.lib.niu.edu'
    url = 'http://commons.lib.niu.edu/oai/request'
    provider_link_id = 'commons.lib.niu.edu'
