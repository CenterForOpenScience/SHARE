from share.bot import BotAppConfig


class AppConfig(BotAppConfig):
    name = 'bots.elasticsearch'
    version = '0.0.1'
    long_title = ''
    home_page = ''

    def get_bot(self, started_by, last_run=None, es_url=None, es_index=None, es_setup=None):
        from bots.elasticsearch.bot import ElasticSearchBot
        return ElasticSearchBot(self, started_by, last_run=last_run, es_url=es_url, es_index=es_index, es_setup=es_setup)

    # Sources are also indexed as a special case
    INDEX_MODELS = [
        'CreativeWork',
        'Agent',
        'Tag',
        # 'Subject',
    ]
