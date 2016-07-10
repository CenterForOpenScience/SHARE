from share.bot import BotAppConfig


class AppConfig(BotAppConfig):
    name = 'bots.automerge'
    version = '0.0.1'
    long_title = ''
    home_page = ''

    def get_bot(self, started_by):
        from bots.automerge.bot import AutoMergeBot
        return AutoMergeBot(self, started_by)
