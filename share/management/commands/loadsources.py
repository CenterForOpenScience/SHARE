import os
import random
import string
import datetime
import yaml

from django.conf import settings
from django.core.files import File
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from share.models import ShareUser, Harvester, Transformer, SourceConfig, Source

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
            self.update_sources(source_dirs)

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
        if serialized['harvester'] and not Harvester.objects.filter(key=serialized['harvester']).exists():
            print('Missing harvester {}'.format(serialized['harvester']))
            return
        if serialized['transformer'] and not Transformer.objects.filter(key=serialized['transformer']).exists():
            print('Missing transformer {}'.format(serialized['transformer']))
            return
        source_config, _ = SourceConfig.objects.update_or_create(
            label=label,
            defaults={
                'source': source,
                **self.process_defaults(SourceConfig, serialized)
            }
        )

    def get_or_create_user(self, username):
        if ShareUser.objects.filter(username=username).exists():
            return ShareUser.objects.get(username=username)

        user = ShareUser.objects.create_robot_user(
            username=username,
            robot=username,
        )

        Application = apps.get_model('oauth2_provider', 'Application')
        AccessToken = apps.get_model('oauth2_provider', 'AccessToken')
        application_user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
        application = Application.objects.get(user=application_user)
        client_secret = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(64))
        AccessToken.objects.create(
            user=user,
            application=application,
            expires=(timezone.now() + datetime.timedelta(weeks=20 * 52)),  # 20 yrs
            scope=settings.HARVESTER_SCOPES,
            token=client_secret
        )
        return user

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
