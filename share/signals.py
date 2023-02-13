from django.core import management
from django.db.utils import ProgrammingError


def post_migrate_load_sources(sender, **kwargs):
    Source = sender.get_model('Source')
    try:
        Source.objects.all()[0]
    except ProgrammingError:
        return
    management.call_command('loadsources')


def ensure_latest_elastic_mappings(sender, **kwargs):
    from share.search import IndexSetup

    for index_setup in IndexSetup.all_indexes():
        index_setup.pls_setup_as_needed()
