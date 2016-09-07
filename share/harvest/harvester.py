import abc
import json
import time
import types
import logging
import datetime
from typing import Tuple
from typing import Union
from typing import Iterator
from collections import OrderedDict

import arrow
import requests

from django.db import transaction
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


class Harvester(metaclass=abc.ABCMeta):

    # TODO Make this apply across threads
    rate_limit = (5, 1)  # Rate limit in requests per_second

    def __init__(self, app_config):
        self.last_call = 0
        self.config = app_config
        self.rate_limit = getattr(self.config, 'rate_limit', self.rate_limit)
        self.allowance = self.rate_limit[0]

    @property
    def requests(self) -> requests:
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
        return self.config.user

    @abc.abstractmethod
    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:
        """Fetch date from this provider inside of the given date range.

        Any HTTP[S] requests MUST be sent using the self.requests client.
        It will automatically in force rate limits

        Args:
            start_date (datetime):
            end_date (datetime):

        Returns:
            Iterator<Tuple<str, str|dict|bytes>>: The fetched data paired with
            the unique ID that this provider uses.

            [
                ('1', {'my': 'doc'}),
                ('2', {'your': 'doc'}),
            ]
        """
        raise NotImplementedError

    def shift_range(self, start_date: arrow.Arrow, end_date: arrow.Arrow) -> arrow.Arrow:
        """Most providers will not need this method.

        For providers that should be collecting data at an offset, see figshare.

        Args:
            start_date (datetime):
            end_date (datetime):

        Returns:
            (datetime, datetime): The shifted date range
        """
        return start_date, end_date

    def harvest(self, start_date: [datetime.datetime, datetime.timedelta, arrow.Arrow], end_date: [datetime.datetime, datetime.timedelta, arrow.Arrow], shift_range: bool=True) -> list:
        from share.models import RawData
        start_date, end_date = self._validate_dates(start_date, end_date)

        stored = []
        with transaction.atomic():
            rawdata = self.do_harvest(start_date, end_date)
            assert isinstance(rawdata, types.GeneratorType), 'do_harvest did not return a generator type, found {!r}. Make sure to use the yield keyword'.format(type(rawdata))

            for doc_id, datum in rawdata:
                stored.append(RawData.objects.store_data(doc_id, self.encode_data(datum), self.source, self.config.label))

        return stored

    def raw(self, start_date: [datetime.datetime, datetime.timedelta, arrow.Arrow], end_date: [datetime.datetime, datetime.timedelta, arrow.Arrow], shift_range: bool=True, limit: int=None) -> list:
        start_date, end_date = self._validate_dates(start_date, end_date)
        count, harvest = 0, self.do_harvest(start_date, end_date)
        assert isinstance(harvest, types.GeneratorType), 'do_harvest did not return a generator type, found {!r}. Make sure to use the yield keyword'.format(type(harvest))

        for doc_id, datum in harvest:
            yield doc_id, self.encode_data(datum, pretty=True)
            count += 1
            if limit and count >= limit:
                break

    def encode_data(self, data, pretty=False) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, dict):
            return self.encode_json(data, pretty=pretty)
        if isinstance(data, str):
            return data.encode()
        raise Exception('Unable to properly encode data blob {!r}. Data should be a dict, bytes, or str objects.'.format(data))

    def encode_json(self, data: dict, pretty: bool=False) -> bytes:
        """Orders a python dict recursively so it will always hash to the
        same value. Used for Dedupping harvest results
        Args:
            data (dict):

        Returns:
            str: json.dumpsed ordered dictionary
        """
        return json.dumps(data, sort_keys=True, indent=4 if pretty else None).encode()

    def _validate_dates(self, start_date, end_date):
        assert not (bool(start_date) ^ bool(end_date)), 'Must specify both a start and end date or neither'
        assert isinstance(start_date, (datetime.timedelta, datetime.datetime, arrow.Arrow)) and isinstance(end_date, (datetime.timedelta, datetime.datetime, arrow.Arrow)), 'start_date and end_date must be either datetimes or timedeltas'
        assert not (isinstance(start_date, datetime.timedelta) and isinstance(end_date, datetime.timedelta)), 'Only one of start_date and end_date may be a timedelta'

        if isinstance(start_date, datetime.datetime):
            start_date = arrow.get(start_date)

        if isinstance(end_date, datetime.datetime):
            end_date = arrow.get(end_date)

        if isinstance(start_date, datetime.timedelta):
            start_date = arrow.get(end_date + start_date)

        if isinstance(end_date, datetime.timedelta):
            end_date = arrow.get(start_date + end_date)

        og_start, og_end = start_date, end_date
        start_date, end_date = self.shift_range(start_date, end_date)
        assert isinstance(start_date, arrow.Arrow) and isinstance(end_date, arrow.Arrow), 'transpose_time_window must return a tuple of 2 datetimes'

        if (og_start, og_end) != (start_date, end_date):
            logger.warning('Date shifted from {} - {} to {} - {}. Disable shifting by passing shift_range=False'.format(og_start, og_end, start_date, end_date))

        assert start_date < end_date, 'start_date must be before end_date {} < {}'.format(start_date, end_date)

        return start_date, end_date
