import abc
import json
import logging

from django.apps import apps
from django.db import migrations
from django.apps import AppConfig

from celery.schedules import crontab

logger = logging.getLogger(__name__)


class ProviderAppConfig(AppConfig, metaclass=abc.ABCMeta):

    @abc.abstractproperty
    def title(self):
        raise NotImplementedError

    @abc.abstractproperty
    def home_page(self):
        raise NotImplementedError

    @abc.abstractproperty
    def harvester(self):
        raise NotImplementedError

    @abc.abstractproperty
    def normalizer(self):
        raise NotImplementedError

    def as_source(self):
        from share.models import ShareSource
        return ShareSource.objects.get(name=self.name)


class ProviderMigration:

    def __init__(self, app_config):
        self.config = app_config

    def ops(self):
        return [
            migrations.RunPython(
                ProviderSourceMigration(self.config.label),
                # ProviderSourceMigration(self.config.label).reverse,
            ),
            migrations.RunPython(
                HarvesterScheduleMigration(self.config.label),
                # HarvesterScheduleMigration(self.config.label).reverse,
            ),
            migrations.RunPython(
                NormalizerScheduleMigration(self.config.label),
                # NormalizerScheduleMigration(self.config.label).reverse,
            ),
        ]

    def dependencies(self):
        return [
            ('share', '0001_initial'),
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


class NormalizerScheduleMigration(AbstractProviderMigration):

    schedule = crontab(hour='*')  # Once an hour

    def __call__(self, apps, schema_editor):
        from djcelery.models import PeriodicTask
        from djcelery.models import CrontabSchedule
        tab = CrontabSchedule.from_schedule(self.schedule)
        tab.save()
        PeriodicTask(
            name='{} normalizer task'.format(self.config.title),
            task='share.tasks.run_normalizer',
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


class ProviderSourceMigration(AbstractProviderMigration):

    def __call__(self, apps, schema_editor):
        from share.models import ShareSource
        ShareSource.objects.get_or_create(
            name=self.config.name,
            # self.app_config.title,
        )[0].save()

    def reverse(self, apps, schema_editor):
        from share.models import ShareSource
        try:
            ShareSource.objects.get(name=self.config.name).delete()
        except ShareSource.DoesNotExist:
            pass
