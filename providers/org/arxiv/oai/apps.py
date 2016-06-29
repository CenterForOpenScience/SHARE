from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.arxiv.oai'
    title = 'arxiv'
    long_title = 'ArXiv'
    home_page = 'https://arxiv.org'
    rate_limit = (1, 3)
    url = 'http://export.arxiv.org/oai2'
    time_granularity = False
