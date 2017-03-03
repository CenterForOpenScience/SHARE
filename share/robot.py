import abc
import json

from django.apps import apps
from django.db import migrations
from django.apps import AppConfig
from django.utils.functional import cached_property


class RobotAppConfig(AppConfig, metaclass=abc.ABCMeta):

    disabled = False

    @abc.abstractproperty
    def version(self):
        raise NotImplementedError

    @abc.abstractproperty
    def task(self):
        raise NotImplementedError

    @abc.abstractproperty
    def task_name(self):
        raise NotImplementedError

    @abc.abstractproperty
    def description(self):
        raise NotImplementedError

    @abc.abstractproperty
    def schedule(self):
        raise NotImplementedError

    @cached_property
    def user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(robot=self.name)


class AbstractRobotMigration:

    def __init__(self, label):
        self.config = apps.get_app_config(label)
        if not isinstance(self.config, RobotAppConfig):
            raise Exception('Found non-robot app, "{}", in a robot migration.'.format(label))

    def deconstruct(self):
        return ('{}.{}'.format(__name__, self.__class__.__name__), (self.config.label, ), {})


class RobotMigrations:

    def __init__(self, app_config):
        self.config = app_config

    def migrations(self):
        return [InitialMigration(self.config).migration()]


class InitialMigration:

    def __init__(self, app_config):
        self.config = app_config

    def ops(self):
        return [
            migrations.RunPython(
                RobotUserMigration(self.config.label),
                # RobotUserMigration(self.config.label).reverse,
            ),
            migrations.RunPython(
                RobotScheduleMigration(self.config.label),
                # RobotScheduleMigration(self.config.label).reverse,
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


class RobotUserMigration(AbstractRobotMigration):
    def __call__(self, apps, schema_editor):
        ShareUser = apps.get_model('share', 'ShareUser')
        ShareUser.objects.create_robot_user(
            username=self.config.name,
            robot=self.config.name,
        )

    def reverse(self, apps, schema_editor):
        ShareUser = apps.get_model('share', 'ShareUser')
        try:
            ShareUser.objects.get(username=self.config.name, harvester=self.config.name).delete()
        except ShareUser.DoesNotExist:
            pass


class RobotScheduleMigration(AbstractRobotMigration):

    def __call__(self, apps, schema_editor):
        from djcelery.models import PeriodicTask
        from djcelery.models import CrontabSchedule
        tab = CrontabSchedule.from_schedule(self.config.schedule)
        tab.save()
        PeriodicTask(
            enabled=not self.config.disabled,
            name=self.config.task_name,
            task=self.config.task,
            description=self.config.description,
            args=json.dumps([1, self.config.label]),  # Note 1 should always be the system user
            crontab=tab,
        ).save()

    def reverse(self, apps, schema_editor):
        PeriodicTask = apps.get_model('djcelery', 'PeriodicTask')
        try:
            PeriodicTask.get(
                task=self.config.task,
                args=json.dumps([1, self.config.label]),  # Note 1 should always be the system user
            ).delete()
        except PeriodicTask.DoesNotExist:
            pass


class DisableRobotScheduleMigration(AbstractRobotMigration):

    def __call__(self, apps, schema_editor):
        PeriodicTask = apps.get_model('djcelery', 'PeriodicTask')

        PeriodicTask.objects.filter(
            task=self.config.task,
            args=json.dumps([1, self.config.label]),  # Note 1 should always be the system user
        ).update(enabled=False)
