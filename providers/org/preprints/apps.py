from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.preprints'
    version = '0.0.1'
    title = 'Preprints'
    long_title = 'Preprints'
    home_page = 'http://www.preprints.org'
    url = 'http://www.preprints.org/oaipmh/'
    time_granularity = False
    emitted_type = 'preprint'
