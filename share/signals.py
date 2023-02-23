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
    from share.search import IndexStrategy

    for index_strategy in IndexStrategy.for_all_indexes():
        index_strategy.pls_setup_as_needed()
