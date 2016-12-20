from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.philpapers'
    version = '0.0.1'
    title = 'PhilPapers'
    long_title = 'PhilPapers'
    home_page = 'http://philpapers.org'
    url = 'http://philpapers.org/oai.pl'
    time_granularity = False
    emitted_type = 'preprint'
