from share.bot import BotAppConfig


class AppConfig(BotAppConfig):
    name = 'bots.autocurate.tag'
    version = '0.0.1'
    long_title = ''
    home_page = ''

    def get_bot(self, started_by, last_run=None):
        from .bot import AutoCurateBot
        return AutoCurateBot(self, started_by, last_run=last_run)
