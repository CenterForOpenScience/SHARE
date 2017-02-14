from django.core import management


def post_migrate_load_sources(sender, **kwargs):
    management.call_command('loadsources')
