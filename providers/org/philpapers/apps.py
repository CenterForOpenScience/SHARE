from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.philpapers'
    version = '0.0.1'
    title = 'PhilPapers'
    long_title = 'PhilPapers'
    home_page = 'http://philpapers.org'
    url = 'http://philpapers.org/oai.pl'
    time_granularity = False
    until_param = 'to'
    emitted_type = 'publication'
    type_map = {
        'info:eu-repo/semantics/article': 'article',
        'info:eu-repo/semantics/book': 'book',
        # 'info:eu-repo/semantics/review': 'review',
    }
