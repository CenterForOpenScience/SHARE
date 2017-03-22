from django.apps import AppConfig
from django.db.models.signals import post_migrate
from share.signals import post_migrate_load_sources


class ShareConfig(AppConfig):
    name = 'share'

    def ready(self):
        post_migrate.connect(post_migrate_load_sources, sender=self)
