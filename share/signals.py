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
    from share.search.elastic_manager import ElasticManager
    elastic_manager = ElasticManager()

    for index_name in elastic_manager.get_primary_indexes():
        elastic_manager.update_mappings(index_name)
