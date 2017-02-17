import abc
import json
import os
import random
import string
import datetime

from django.apps import apps
from django.db import migrations
from django.conf import settings
from django.core.files import File
from django.apps import AppConfig
from django.utils import timezone
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
        from share.provider import ProviderAppConfig
        migrations = [InitialMigration(self.config).migration()]
        if isinstance(self.config, ProviderAppConfig):
            migrations.append(FaviconMigration(self.config).migration())
        return migrations


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
                RobotOauthTokenMigration(self.config.label),
                # RobotOauthTokenMigration(self.config.label).reverse,
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


class FaviconMigration:

    def __init__(self, app_config):
        self.config = app_config

    def ops(self):
        return [
            migrations.RunPython(
                RobotFaviconMigration(self.config.label),
                # RobotFaviconMigration(self.config.label).reverse,
            ),
        ]

    def dependencies(self):
        return [
            (self.config.label, '0001_initial'),
            ('share', '0018_store_favicons'),
        ]

    def migration(self):
        m = migrations.Migration('0002_favicon', self.config.label)
        m.operations = self.ops()
        m.dependencies = self.dependencies()
        return m


class RobotUserMigration(AbstractRobotMigration):
    def __call__(self, apps, schema_editor):
        ShareUser = apps.get_model('share', 'ShareUser')
        ShareUser.objects.create_robot_user(
            username=self.config.name,
            robot=self.config.name,
            long_title=self.config.long_title,
            home_page=self.config.home_page
        )

    def reverse(self, apps, schema_editor):
        ShareUser = apps.get_model('share', 'ShareUser')
        try:
            ShareUser.objects.get(username=self.config.name, harvester=self.config.name).delete()
        except ShareUser.DoesNotExist:
            pass


class RobotOauthTokenMigration(AbstractRobotMigration):

    def __call__(self, apps, schema_editor):
        ShareUser = apps.get_model('share', 'ShareUser')
        Application = apps.get_model('oauth2_provider', 'Application')
        AccessToken = apps.get_model('oauth2_provider', 'AccessToken')
        migration_user = ShareUser.objects.get(username=self.config.name, robot=self.config.name)
        application_user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
        application = Application.objects.get(user=application_user)
        client_secret = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(64))
        AccessToken.objects.create(
            user=migration_user,
            application=application,
            expires=(timezone.now() + datetime.timedelta(weeks=20 * 52)),  # 20 yrs
            scope=settings.HARVESTER_SCOPES,
            token=client_secret
        )

    def reverse(self, apps, schema_editor):
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


class RobotFaviconMigration(AbstractRobotMigration):

    def __call__(self, apps, schema_editor):
        user = self.config.user
        try:
            self._save_favicon(user, os.path.join(self.config.path, 'favicon.ico'))
        except OSError:
            # Try parent directory
            self._save_favicon(user, os.path.join(os.path.dirname(self.config.path), 'favicon.ico'))

    def _save_favicon(self, user, path):
        with open(path, 'rb') as f:
            user.favicon.save(user.username, File(f))

    def reverse(self, apps, schema_editor):
        ShareUser = apps.get_model('share', 'ShareUser')
        try:
            self.config.user.favicon.delete()
        except ShareUser.DoesNotExist:
            pass
