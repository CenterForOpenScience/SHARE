from share.bot import BotAppConfig


class AppConfig(BotAppConfig):
    name = 'bots.autocurateperson'
    version = '0.0.1'
    long_title = ''
    home_page = ''

    def get_bot(self):
        from .bot import AutoCurateBot
        return AutoCurateBot(self)
