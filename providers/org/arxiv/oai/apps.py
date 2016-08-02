from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.arxiv.oai'
    title = 'arxiv'
    long_title = 'ArXiv'
    home_page = 'https://arxiv.org'
    rate_limit = (1, 3)
    url = 'http://export.arxiv.org/oai2'
    time_granularity = False
    version = '0.0.0'
    emitted_type = 'preprint'
    disabled = True  # superceeded by org.arxiv

    @property
    def user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(robot='providers.org.arxiv')
