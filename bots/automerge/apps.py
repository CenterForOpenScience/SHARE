from share.bot import BotAppConfig

from bots.automerge.bot import AutoMergeBot


class AppConfig(BotAppConfig):
    name = 'bots.automerge'

    bot = AutoMergeBot
