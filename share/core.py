import json
import logging
import datetime

import requests

from django.db import transaction
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


# NOTE: Have to use relative imports here because Django hates fun
class Harvester:

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

    def harvest(self, start_date=None, end_date=None):
        from share.models import RawData
        assert not (bool(start_date) ^ bool(end_date)), 'Must specify both a start and end date or neither'
        assert isinstance(start_date, (datetime.timedelta, datetime.datetime)) and isinstance(start_date, (datetime.timedelta, datetime.datetime)), 'start_date and end_date must be either datetimes or timedeltas'
        assert not (isinstance(start_date, datetime.timedelta) and isinstance(end_date, datetime.timedelta)), 'Only one of start_date and end_date may be a timedelta'

        if isinstance(start_date, datetime.timedelta):
            start_date = end_date + start_date

        if isinstance(end_date, datetime.timedelta):
            end_date = start_date + end_date

        assert start_date < end_date, 'start_date must be before end_date {} < {}'.format(start_date, end_date)

        stored = []
        with transaction.atomic():
            rawdata = self.do_harvest(start_date, end_date)

            # assert isinstance(rawdata, (list, tuple)), 'Expected self.do_harvest to return a list or tuple. Got {}'.format(rawdata)
            for doc_id, datum in rawdata:
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


class CreateHarvesterUser:

    def __init__(self, app_config):
        self.app_config = app_config

    def __call__(self, apps, schema_editor):
        from share.models import ShareUser
        from django.contrib.auth.models import User

        user = User.objects.create_user(
            self.app_config.TITLE,
            email=None,
            password=None,
        )

        user.save()

        share_user = ShareUser(user=user, is_entity=True)
        share_user.save()

        return share_user


class RemoveHarvesterUser:

    def __init__(self, app_config):
        self.app_config = app_config

    def __call__(self, apps, schema_editor):
        from django.contrib.auth.models import User
        User.objects.get(username=self.app_config.TITLE).delete()
