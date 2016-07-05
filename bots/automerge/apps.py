from share.bot import BotAppConfig


class AppConfig(BotAppConfig):
    name = 'bots.automerge'
    version = '0.0.1'

    def get_bot(self):
        from bots.automerge.bot import AutoMergeBot
        return AutoMergeBot(self)
