from share.bot import BotAppConfig


class AppConfig(BotAppConfig):
    name = 'bots.elasticsearch'
    version = '0.0.1'
    long_title = ''
    home_page = ''

    def get_bot(self, started_by):
        from bots.elasticsearch.bot import ElasticSearchBot
        return ElasticSearchBot(self, started_by)
