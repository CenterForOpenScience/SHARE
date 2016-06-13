import json
import logging
import datetime
from collections import OrderedDict

import requests

from django.apps import apps
from django.db import migrations
from django.db import transaction
from django.apps import AppConfig
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


# NOTE: Have to use relative imports here because Django hates fun
class Harvester:

    # Callable that takes (start_date, end_date) and returns a tuple (start_date, end_date)
    # For providers that should be collecting data at an offset. See figshare
    shift_range = None

    @property
    def requests(self):
        return requests  # TODO override w/ rate limitting requests

    @cached_property
    def user(self):
        from django.contrib.auth.models import User
        return User.objects.get(username=self.config.TITLE)

    @cached_property
    def share_user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(user=self.user)

    def __init__(self, app_config):
        self.config = app_config

    def harvest(self, start_date=None, end_date=None, shift_range=True):
        from share.models import RawData
        assert not (bool(start_date) ^ bool(end_date)), 'Must specify both a start and end date or neither'
        assert isinstance(start_date, (datetime.timedelta, datetime.datetime)) and isinstance(start_date, (datetime.timedelta, datetime.datetime)), 'start_date and end_date must be either datetimes or timedeltas'
        assert not (isinstance(start_date, datetime.timedelta) and isinstance(end_date, datetime.timedelta)), 'Only one of start_date and end_date may be a timedelta'

        if isinstance(start_date, datetime.timedelta):
            start_date = end_date + start_date

        if isinstance(end_date, datetime.timedelta):
            end_date = start_date + end_date

        assert start_date < end_date, 'start_date must be before end_date {} < {}'.format(start_date, end_date)

        if callable(self.config.transpose_time_window):
            start_date, end_date = self.config.transpose_time_window(start_date, end_date)
            assert isinstance(start_date, datetime.datetime) and isinstance(start_date, datetime.datetime), 'transpose_time_window must return a tuple of 2 datetimes'
            assert start_date < end_date, 'start_date must be before end_date {} < {}'.format(start_date, end_date)

        if shift_range and callable(self.shift_range):
            og_start, og_end = start_date, end_date
            start_date, end_date = self.shift_range(start_date, end_date)
            logger.warning('Date shifted from {} - {} to {} - {}. Disable shifting by passing shift_range=False'.format(og_start, og_end, start_date, end_date))

        stored = []
        with transaction.atomic():
            rawdata = self.do_harvest(start_date, end_date)

            for doc_id, datum in rawdata:
                if isinstance(datum, dict):
                    datum = self.encode_json(datum)
                elif isinstance(datum, str):
                    datum = datum.encode()
                assert isinstance(datum, bytes), 'Found non-bytes item {} in results of self.do_harvest'.format(datum)
                stored.append(RawData.objects.store_data(doc_id, datum, self.share_user))

        logger.info('Collected {} data blobs from {}'.format(len(stored), self.config.TITLE))

    def encode_json(self, data):
        def order_json(data):
            return OrderedDict(sorted([
                (key, order_json(value) if isinstance(value, dict) else value)
                for key, value in data.items()
            ], key=lambda x: x[0]))
        return json.dumps(order_json(data)).encode()


class ProviderAppConfig(AppConfig):
    pass


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


class HarvesterScheduleMigration:

    def __init__(self, label):
        self.config = apps.get_app_config(label)

    def __call__(self, apps, schema_editor):
        from djcelery.models import PeriodicTask
        from djcelery.models import CrontabSchedule
        tab = crontab=CrontabSchedule.from_schedule(self.config.SCHEDULE)
        tab.save()
        PeriodicTask(
            name='{} harvester task'.format(self.config.TITLE),
            task='share.tasks.run_harvester',
            description='TODO',
            args=json.dumps([self.config.name]),
            crontab=tab,
        ).save()

    def reverse(self, apps, schema_editor):
        from djcelery.models import PeriodicTask
        try:
            PeriodicTask.get(
                name='{} harvester task'.format(self.config.TITLE),
                task='share.tasks.run_harvester',
                args=json.dumps([self.config.name]),
            ).delete()
        except PeriodicTask.DoesNotExist:
            pass

    def deconstruct(self):
        return ('{}.{}'.format(__name__, self.__class__.__name__), (self.label, ), {})


class ProviderSourceMigration:

    def __init__(self, label):
        self.config = apps.get_app_config(label)

    def __call__(self, apps, schema_editor):
        from share.models import ShareSource
        ShareSource.objects.get_or_create(
            name=self.config.name,
            # self.app_config.TITLE,
        )[0].save()

    def reverse(self, apps, schema_editor):
        from share.models import ShareSource
        try:
            ShareSource.objects.get(name=self.config.name).delete()
        except ShareSource.DoesNotExist:
            pass

    def deconstruct(self):
        return ('{}.{}'.format(__name__, self.__class__.__name__), (self.label, ), {})
