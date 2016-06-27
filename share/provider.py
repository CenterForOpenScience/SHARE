import abc
import datetime
import json
import logging
import random
import string

from django.apps import apps
from django.db import migrations
from django.apps import AppConfig
from django.utils import timezone

from celery.schedules import crontab

from share.harvest.oai import OAIHarvester
from share.normalize import Normalizer
from share.normalize.oai import OAINormalizer

logger = logging.getLogger(__name__)


class ProviderAppConfig(AppConfig, metaclass=abc.ABCMeta):

    schedule = crontab(minute=0, hour=0)

    @abc.abstractproperty
    def title(self):
        raise NotImplementedError

    @abc.abstractproperty
    def long_title(self):
        raise NotImplementedError

    @abc.abstractproperty
    def home_page(self):
        raise NotImplementedError

    @abc.abstractproperty
    def harvester(self):
        raise NotImplementedError

    @property
    def label(self):
        return self.name.rpartition('providers.')[2]

    @property
    def normalizer(self):
        return Normalizer

    @property
    def user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(harvester=self.name)

    def authorization(self) -> str:
        return 'Bearer ' + self.user.accesstoken_set.first().token


class OAIProviderAppConfig(ProviderAppConfig, metaclass=abc.ABCMeta):

    rate_limit = (5, 1)

    @abc.abstractproperty
    def url(self):
        return NotImplementedError

    @property
    def harvester(self):
        return OAIHarvester

    @property
    def normalizer(self):
        return OAINormalizer


class ProviderMigration:

    def __init__(self, app_config):
        self.config = app_config

    def ops(self):
        return [
            migrations.RunPython(
                HarvesterUserMigration(self.config.label),
                # HarvesterUserMigration(self.config.label).reverse,
            ),
            migrations.RunPython(
                HarvesterOauthTokenMigration(self.config.label),
                # HarvesterOauthTokenMigration(self.config.label).reverse,
            ),
            migrations.RunPython(
                HarvesterScheduleMigration(self.config.label),
                # HarvesterScheduleMigration(self.config.label).reverse,
            ),
        ]

    def dependencies(self):
        return [
            ('share', '0001_initial'),
            ('djcelery', '0001_initial'),
        ]

    def migration(self):
        m = migrations.Migration('0001_initial', self.config.label)
        m.operations = self.ops()
        m.dependencies = self.dependencies()
        return m


class AbstractProviderMigration:

    def __init__(self, label):
        self.config = apps.get_app_config(label)

    def deconstruct(self):
        return ('{}.{}'.format(__name__, self.__class__.__name__), (self.config.label, ), {})


class HarvesterUserMigration(AbstractProviderMigration):
    def __call__(self, apps, schema_editor):
        from share.models import ShareUser
        user = ShareUser.objects.create_harvester_user(self.config.name, self.config.name)

    def reverse(self, apps, schema_editor):
        from share.models import ShareUser
        try:
            ShareUser.objects.get(username=self.config.name, harvester=self.config.name).delete()
        except ShareUser.DoesNotExist:
            pass


class HarvesterOauthTokenMigration(AbstractProviderMigration):
    def __call__(self, apps, schema_editor):
        ShareUser = apps.get_model('share', 'ShareUser')
        Application = apps.get_model('oauth2_provider', 'Application')
        AccessToken = apps.get_model('oauth2_provider', 'AccessToken')
        from django.conf import settings
        migration_user = ShareUser.objects.get(username=self.config.name, harvester=self.config.name)
        application_user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
        application = Application.objects.get(user=application_user)
        client_secret = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(64))
        token = AccessToken.objects.create(
            user=migration_user,
            application=application,
            expires=(timezone.now() + datetime.timedelta(weeks=20 * 52)), # 20 yrs
            scope=settings.HARVESTER_SCOPES,
            token=client_secret
        )

    def reverse(self, apps, schema_editor):
        pass


class HarvesterScheduleMigration(AbstractProviderMigration):

    def __call__(self, apps, schema_editor):
        from djcelery.models import PeriodicTask
        from djcelery.models import CrontabSchedule
        tab = CrontabSchedule.from_schedule(self.config.schedule)
        tab.save()
        PeriodicTask(
            name='{} harvester task'.format(self.config.title),
            task='share.tasks.run_harvester',
            description='TODO',
            args=json.dumps([self.config.name]),
            crontab=tab,
        ).save()

    def reverse(self, apps, schema_editor):
        from djcelery.models import PeriodicTask
        try:
            PeriodicTask.get(
                task='share.tasks.run_harvester',
                args=json.dumps([self.config.name]),
            ).delete()
        except PeriodicTask.DoesNotExist:
            pass
