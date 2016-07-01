from share.bot import BotAppConfig


class AppConfig(BotAppConfig):
    name = 'bots.elasticsearch'

    def get_bot(self):
        from bots.elasticsearch.bot import ElasticSearchBot
        return ElasticSearchBot(self)
