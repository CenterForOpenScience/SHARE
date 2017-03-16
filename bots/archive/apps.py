from share.bot import BotAppConfig


class AppConfig(BotAppConfig):
    name = 'bots.archive'
    version = '0.0.1'
    long_title = ''
    home_page = ''

    def get_bot(self, started_by, last_run=None):
        from .bot import ArchiveBot
        return ArchiveBot(self, started_by, last_run)
