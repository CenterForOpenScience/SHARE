import json
import os
import yaml
from stevedore import extension

from celery.schedules import crontab
from djcelery.models import PeriodicTask
from djcelery.models import CrontabSchedule

from django.core.files import File
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from share.models import ShareUser, Source

SOURCES_DIR = 'sources'


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('sources', nargs='*', type=str, help='Names of the sources to load (if omitted, load all)')

    def handle(self, *args, **options):
        sources = options.get('sources')
        sources_dir = os.path.join(apps.get_app_config('share').path, SOURCES_DIR)
        if sources:
            source_dirs = [os.path.join(sources_dir, s) for s in sources]
        else:
            source_dirs = [os.path.join(sources_dir, s) for s in os.listdir(sources_dir)]

        with transaction.atomic():
            self.known_harvesters = self.sync_drivers('share.harvesters', apps.get_model('share.Harvester'))
            self.known_transformers = self.sync_drivers('share.transformers', apps.get_model('share.Transformer'))
            self.update_sources(source_dirs)

    def sync_drivers(self, namespace, model):
        names = set(extension.ExtensionManager(namespace).entry_points_names())
        for key in names:
            model.objects.update_or_create(key=key)
        missing = model.objects.exclude(key__in=names).values_list('key', flat=True)
        if missing:
            print('Warning: Missing {} drivers: {}'.format(model._meta.model_name, missing))
        return names

    def update_sources(self, source_dirs):
        loaded_sources = set()
        loaded_configs = set()
        for source_dir in source_dirs:
            with open(os.path.join(source_dir, 'source.yaml')) as fobj:
                serialized = yaml.load(fobj)
            configs = serialized.pop('configs')
            name = serialized.pop('name')
            assert name not in loaded_sources
            loaded_sources.add(name)

            user = self.get_or_create_user(serialized.pop('user'))
            source, _ = Source.objects.update_or_create(
                name=name,
                defaults={
                    'user': user,
                    **self.process_defaults(Source, serialized)
                }
            )
            with open(os.path.join(source_dir, 'icon.ico'), 'rb') as fobj:
                source.icon.save(name, File(fobj))
            for config in configs:
                assert config['label'] not in loaded_configs
                loaded_configs.add(config['label'])
                self.update_source_config(source, config)

    def update_source_config(self, source, serialized):
        label = serialized.pop('label')
        if serialized['harvester'] and serialized['harvester'] not in self.known_harvesters:
            print('Unknown harvester {}! Skipping source config {}'.format(serialized['harvester'], label))
            return
        if serialized['transformer'] and serialized['transformer'] not in self.known_transformers:
            print('Unknown transformer {}! Skipping source config {}'.format(serialized['transformer'], label))
            return
        source_config, _ = apps.get_model('share.SourceConfig').objects.update_or_create(
            label=label,
            defaults={
                'source': source,
                **self.process_defaults(apps.get_model('share.SourceConfig'), serialized)
            }
        )
        self.schedule_harvest_task(source_config.label, source_config.disabled)

    def get_or_create_user(self, username):
        try:
            return ShareUser.objects.get(username=username)
        except ShareUser.DoesNotExist:
            return ShareUser.objects.create_robot_user(
                username=username,
                robot=username,
            )

    def schedule_harvest_task(self, label, disabled):
        task_name = '{} harvester task'.format(label)
        tab = CrontabSchedule.from_schedule(crontab(minute=0, hour=0))
        tab.save()
        PeriodicTask.objects.update_or_create(
            name=task_name,
            defaults={
                'enabled': not disabled,
                'task': 'share.tasks.HarvesterTask',
                'description': 'Harvesting',
                'args': json.dumps([1, label]),  # Note 1 should always be the system user
                'crontab': tab,
            }
        )

    def process_defaults(self, model, defaults):
        ret = {}
        for k, v in defaults.items():
            field = model._meta.get_field(k)
            if field.is_relation and v is not None:
                natural_key = tuple(v) if isinstance(v, list) else (v,)
                ret[k] = field.related_model.objects.get_by_natural_key(natural_key)
            else:
                ret[k] = v
        return ret
