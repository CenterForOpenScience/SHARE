from share.bot import BotAppConfig


class AppConfig(BotAppConfig):
    name = 'bots.elasticsearch'
    version = '0.0.1'
    long_title = ''
    home_page = ''

    def get_bot(self, started_by, last_run=None):
        from bots.elasticsearch.bot import ElasticSearchBot
        return ElasticSearchBot(self, started_by, last_run=last_run)

    # Sources are also indexed as a special case
    INDEX_MODELS = [
        'AbstractCreativeWork',
        'Entity',
        'Person',
        'Tag',
    ]
