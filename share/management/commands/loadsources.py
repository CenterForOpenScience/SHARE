import os
import yaml
from stevedore import extension

from django.apps import apps
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.dispatch import receiver
from django.core.exceptions import FieldDoesNotExist
from django.db.models.signals import post_save

import share
from share.models.core import user_post_save

SOURCES_DIR = 'sources'


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('sources', nargs='*', type=str, help='Names of the sources to load (if omitted, load all)')
        parser.add_argument('--overwrite', action='store_true', help='Overwrite existing sources and source configs')

    def handle(self, *args, **options):
        # If we're running in a migrations we need to use the correct apps
        self.apps = options.get('apps', apps)

        sources = options.get('sources')
        sources_dir = os.path.join(share.__path__[0], SOURCES_DIR)
        if sources:
            source_dirs = [os.path.join(sources_dir, s) for s in sources]
        else:
            source_dirs = [os.path.join(sources_dir, s) for s in os.listdir(sources_dir)]

        if self.apps.get_model('share.ShareUser').__module__ == '__fake__':
            receiver(post_save, sender=self.apps.get_model('share.ShareUser'), dispatch_uid='__fake__.share.models.share_user_post_save_handler')(user_post_save)

        with transaction.atomic():
            self.known_harvesters = self.sync_drivers('share.harvesters', self.apps.get_model('share.Harvester'))
            self.known_transformers = self.sync_drivers('share.transformers', self.apps.get_model('share.Transformer'))
            self.update_sources(source_dirs, overwrite=options.get('overwrite'))

    def sync_drivers(self, namespace, model):
        names = set(extension.ExtensionManager(namespace).entry_points_names())
        for key in names:
            model.objects.update_or_create(key=key)
        missing = model.objects.exclude(key__in=names).values_list('key', flat=True)
        if missing:
            print('Warning: Missing {} drivers: {}'.format(model._meta.model_name, missing))
        return names

    def update_sources(self, source_dirs, overwrite):
        Source = self.apps.get_model('share.Source')
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
            source_defaults = {
                'user': user,
                **self.process_defaults(Source, serialized)
            }
            if overwrite:
                source, _ = Source.objects.update_or_create(name=name, defaults=source_defaults)
            else:
                source, _ = Source.objects.get_or_create(name=name, defaults=source_defaults)

            with open(os.path.join(source_dir, 'icon.ico'), 'rb') as fobj:
                source.icon.save(name, File(fobj))
            for config in configs:
                assert config['label'] not in loaded_configs
                loaded_configs.add(config['label'])
                self.update_source_config(source, config, overwrite)

    def update_source_config(self, source, serialized, overwrite):
        label = serialized.pop('label')
        if serialized['harvester'] and serialized['harvester'] not in self.known_harvesters:
            print('Unknown harvester {}! Skipping source config {}'.format(serialized['harvester'], label))
            return
        if serialized['transformer'] and serialized['transformer'] not in self.known_transformers:
            print('Unknown transformer {}! Skipping source config {}'.format(serialized['transformer'], label))
            return

        SourceConfig = self.apps.get_model('share.SourceConfig')
        config_defaults = {
            'source': source,
            **self.process_defaults(SourceConfig, serialized)
        }
        if overwrite:
            source_config, created = SourceConfig.objects.update_or_create(label=label, defaults=config_defaults)
        else:
            source_config, created = SourceConfig.objects.get_or_create(label=label, defaults=config_defaults)

    def get_or_create_user(self, username):
        ShareUser = self.apps.get_model('share.ShareUser')

        try:
            return ShareUser.objects.get(username=username)
        except ShareUser.DoesNotExist:
            return ShareUser.objects.create_robot_user(
                username=username,
                robot=username,
            )

    def process_defaults(self, model, defaults):
        ret = {}
        for k, v in defaults.items():
            try:
                field = model._meta.get_field(k)
            except FieldDoesNotExist:
                # This script gets run by the migrations fairly early on
                # If new fields have been added the original run of this script will
                # fail unless we ignore those fields.
                self.stderr.write('Found extra field {}, skipping...'.format(k))
                continue
            if field.is_relation and v is not None:
                natural_key = tuple(v) if isinstance(v, list) else (v,)
                ret[k] = field.related_model.objects.get_by_natural_key(natural_key)
            else:
                ret[k] = v
        return ret
