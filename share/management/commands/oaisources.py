from django.core.management.base import BaseCommand

from share.models import SourceConfig


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--prefix', type=str, help='Metadata prefix to filter by')

    def handle(self, *args, **options):
        prefix = options.get('prefix')

        oai_configs = SourceConfig.objects.filter(harvester__key='oai').order_by('base_url').distinct('base_url').select_related('source')

        errors = []
        for config in oai_configs:
            try:
                if not prefix or prefix in config.get_harvester().metadata_formats():
                    print('{} ({})'.format(config.source.name, config.base_url))
            except Exception as e:
                errors.append('{} ({}): {}'.format(config.source.name, config.base_url, e))

        if errors:
            print('\nErrors:')
            for e in errors:
                print(e)
