from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.sldr'
    version = '0.0.1'
    title = 'sldr'
    long_title = 'Speech and Language Data Repository (SLDR/ORTOLANG)'
    home_page = 'http://sldr.org'
    url = 'http://sldr.org/oai-pmh.php'
    timezone_granularity = False
