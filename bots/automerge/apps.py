from share.bot import BotAppConfig


class AppConfig(BotAppConfig):
    name = 'bots.automerge'

    def get_bot(self):
        from bots.automerge.bot import AutoMergeBot
        return AutoMergeBot(self)
