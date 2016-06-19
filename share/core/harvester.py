import abc
import json
import time
import logging
import datetime
from collections import OrderedDict

import requests

from django.db import transaction
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


# NOTE: Have to use relative imports here because Django hates fun
class Harvester(metaclass=abc.ABCMeta):

    rate_limit = (5, 1)  # Rate limit in requests per_second

    @property
    def requests(self):
        if self.allowance < 1:
            try:
                time.sleep(self.rate_limit[1] - (time.time() - self.last_call))
            except ValueError:
                pass  # ValueError indicates a negative sleep time
            self.allowance = self.rate_limit[0]
        self.allowance -= 1
        self.last_call = time.time()
        return requests

    @cached_property
    def source(self):
        return self.config.as_source()

    def __init__(self, app_config):
        self.last_call = 0
        self.config = app_config
        self.allowance = self.rate_limit[0]

    @abc.abstractmethod
    def do_harvest(self, start_date, end_date):
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_records(self, url):
        raise NotImplementedError

    # Callable that takes (start_date, end_date) and returns a tuple (start_date, end_date)
    # For providers that should be collecting data at an offset. See figshare
    def shift_range(self, start_date, end_date):
        return start_date, end_date

    def harvest(self, start_date=None, end_date=None, shift_range=True):
        from share.models import RawData
        assert not (bool(start_date) ^ bool(end_date)), 'Must specify both a start and end date or neither'
        assert isinstance(start_date, (datetime.timedelta, datetime.datetime)) and isinstance(start_date, (datetime.timedelta, datetime.datetime)), 'start_date and end_date must be either datetimes or timedeltas'
        assert not (isinstance(start_date, datetime.timedelta) and isinstance(end_date, datetime.timedelta)), 'Only one of start_date and end_date may be a timedelta'

        if isinstance(start_date, datetime.timedelta):
            start_date = end_date + start_date

        if isinstance(end_date, datetime.timedelta):
            end_date = start_date + end_date

        og_start, og_end = start_date, end_date
        start_date, end_date = self.shift_range(start_date, end_date)
        assert isinstance(start_date, datetime.datetime) and isinstance(start_date, datetime.datetime), 'transpose_time_window must return a tuple of 2 datetimes'

        if (og_start, og_end) != (start_date, end_date):
            logger.warning('Date shifted from {} - {} to {} - {}. Disable shifting by passing shift_range=False'.format(og_start, og_end, start_date, end_date))

        assert start_date < end_date, 'start_date must be before end_date {} < {}'.format(start_date, end_date)

        stored = []
        with transaction.atomic():
            rawdata = self.do_harvest(start_date, end_date)

            for doc_id, datum in rawdata:
                if isinstance(datum, dict):
                    datum = self.encode_json(datum)
                elif isinstance(datum, str):
                    datum = datum.encode()
                assert isinstance(datum, bytes), 'Found non-bytes item {} in results of self.do_harvest'.format(datum)
                stored.append(RawData.objects.store_data(doc_id, datum, self.source))

        logger.info('Collected {} data blobs from {}'.format(len(stored), self.config.title))

    # Orders a python dict recursively so it will always hash to the
    # same value. Used for Dedupping harvest results
    def encode_json(self, data):
        def order_json(data):
            return OrderedDict(sorted([
                (key, order_json(value) if isinstance(value, dict) else value)
                for key, value in data.items()
            ], key=lambda x: x[0]))
        return json.dumps(order_json(data)).encode()
