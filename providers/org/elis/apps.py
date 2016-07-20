from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.elis'
    version = '0.0.1'
    title = 'e-LIS'
    long_title = 'Eprints in Library and Information Science'
    home_page = 'eprints.rclis.org'
    url = 'http://eprints.rclis.org/cgi/oai2'
    time_granularity = False
    emitted_type = 'publication'
