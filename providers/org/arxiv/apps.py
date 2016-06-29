from share.provider import ProviderAppConfig


class AppConfig(ProviderAppConfig):
    name = 'providers.org.arxiv'
    title = 'arxiv'
    long_title = 'ArXiv'
    home_page = 'https://arxiv.org'
    rate_limit = (1, 3)
    url = 'http://export.arxiv.org/rss/'
    time_granularity = False
