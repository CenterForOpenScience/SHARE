import abc
import json
import time
import types
import logging
import datetime
from typing import Tuple
from typing import Union
from typing import Iterator

import pendulum
import requests

from django.db import transaction
from django.db.models.base import ModelBase
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


class RateLimittedProxy:

    def __init__(self, proxy_to, calls, per_second):
        self._proxy_to = proxy_to
        self._allowance = calls
        self._calls = calls
        self._last_call = 0
        self._per_second = per_second
        self._cache = {}

    def _check_limit(self):
        if self._allowance > 1:
            return
        wait = self._per_second - (time.time() - self._last_call)
        if wait > 0:
            logger.debug('Rate limitting %s. Sleeping for %s', self._proxy_to, wait)
            time.sleep(wait)
        self._allowance = self._calls
        logger.debug('Access granted for %s', self._proxy_to)

    def _called(self):
        self._allowance -= 1
        self._last_call = time.time()

    def __call__(self, *args, **kwargs):
        self._check_limit()
        ret = self._proxy_to(*args, **kwargs)
        self._called()
        return ret

    def __getattr__(self, name):
        return self._cache.setdefault(name, self.__class__(getattr(self._proxy_to, name), self._calls, self._per_second))


class HarvesterMeta(type):
    def __init__(cls, name, bases, attrs):
        if hasattr(cls, 'registry'):
            assert 'KEY' in attrs and attrs['KEY'] not in cls.registry
            cls.registry[attrs['KEY']] = cls
        else:
            # base class
            cls.registry = {}


class Harvester(metaclass=HarvesterMeta):

    # TODO Make this apply across threads
    rate_limit = (5, 1)  # Rate limit in requests per_second

    def __init__(self, source, **kwargs):
        self.last_call = 0
        self.source = source
        self.kwargs = kwargs
        self.rate_limit = kwargs.get('rate_limit', self.rate_limit)
        self.allowance = self.rate_limit[0]
        self.requests = RateLimittedProxy(requests, *self.rate_limit)

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum, **kwargs) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:
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
        raise NotImplementedError()

    def fetch_by_id(self, provider_id):
        """
        Fetch a document by provider ID.

        Optional to implement, intended for dev and manual testing.

        Args:
            provider_id (str): Unique ID the provider uses to identify works.

        Returns:
            str|dict|bytes: Fetched data.

        """
        raise NotImplementedError()

    def shift_range(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum) -> pendulum.Pendulum:
        """Most providers will not need this method.

        For providers that should be collecting data at an offset, see figshare.

        Args:
            start_date (datetime):
            end_date (datetime):

        Returns:
            (datetime, datetime): The shifted date range
        """
        return start_date, end_date

    def harvest(self, start_date: [datetime.datetime, datetime.timedelta, pendulum.Pendulum], end_date: [datetime.datetime, datetime.timedelta, pendulum.Pendulum], shift_range: bool=True, limit: int=None, **kwargs) -> list:
        from share.models import RawData
        start_date, end_date = self._validate_dates(start_date, end_date)

        raw_ids = []
        with transaction.atomic():
            rawdata = self.do_harvest(start_date, end_date, **kwargs)
            assert isinstance(rawdata, types.GeneratorType), 'do_harvest did not return a generator type, found {!r}. Make sure to use the yield keyword'.format(type(rawdata))

            for doc_id, datum in rawdata:
                raw_ids.append(RawData.objects.store_data(doc_id, self.encode_data(datum), self.source, self.config.label).id)
                if limit is not None and len(raw_ids) >= limit:
                    break

        return raw_ids

    def raw(self, start_date: [datetime.datetime, datetime.timedelta, pendulum.Pendulum], end_date: [datetime.datetime, datetime.timedelta, pendulum.Pendulum], shift_range: bool=True, limit: int=None, **kwargs) -> list:
        start_date, end_date = self._validate_dates(start_date, end_date)
        count, harvest = 0, self.do_harvest(start_date, end_date, **kwargs)
        assert isinstance(harvest, types.GeneratorType), 'do_harvest did not return a generator type, found {!r}. Make sure to use the yield keyword'.format(type(harvest))

        for doc_id, datum in harvest:
            yield doc_id, self.encode_data(datum, pretty=True)
            count += 1
            if limit and count >= limit:
                break

    def harvest_by_id(self, provider_id):
        from share.models import RawData
        datum = self.fetch_by_id(provider_id)
        return RawData.objects.store_data(provider_id, self.encode_data(datum), self.source, self.config.label)

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
        assert isinstance(start_date, (datetime.timedelta, datetime.datetime, pendulum.Pendulum)) and isinstance(end_date, (datetime.timedelta, datetime.datetime, pendulum.Pendulum)), 'start_date and end_date must be either datetimes or timedeltas'
        assert not (isinstance(start_date, datetime.timedelta) and isinstance(end_date, datetime.timedelta)), 'Only one of start_date and end_date may be a timedelta'

        if isinstance(start_date, datetime.datetime):
            start_date = pendulum.instance(start_date)

        if isinstance(end_date, datetime.datetime):
            end_date = pendulum.instance(end_date)

        if isinstance(start_date, datetime.timedelta):
            start_date = pendulum.instance(end_date + start_date)

        if isinstance(end_date, datetime.timedelta):
            end_date = pendulum.instance(start_date + end_date)

        og_start, og_end = start_date, end_date
        start_date, end_date = self.shift_range(start_date, end_date)
        assert isinstance(start_date, pendulum.Pendulum) and isinstance(end_date, pendulum.Pendulum), 'transpose_time_window must return a tuple of 2 datetimes'

        if (og_start, og_end) != (start_date, end_date):
            logger.warning('Date shifted from {} - {} to {} - {}. Disable shifting by passing shift_range=False'.format(og_start, og_end, start_date, end_date))

        assert start_date < end_date, 'start_date must be before end_date {} < {}'.format(start_date, end_date)

        return start_date, end_date
