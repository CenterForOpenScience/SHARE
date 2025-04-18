from django.apps import AppConfig
from django.core import checks
from share.checks import check_all_index_strategies_current


class ShareConfig(AppConfig):
    name = 'share'

    def ready(self):
        checks.register(check_all_index_strategies_current)
