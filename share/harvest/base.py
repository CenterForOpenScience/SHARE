from hashlib import sha256
import abc
import datetime
import logging
import types
import warnings

import pendulum
import requests

from django.conf import settings
from django.utils import timezone

from share.harvest.ratelimit import RateLimittedProxy
from share.harvest.serialization import DeprecatedDefaultSerializer
from share.models import RawDatum


logger = logging.getLogger(__name__)


class FetchResult:
    __slots__ = ('identifier', 'datum', 'datestamp', 'contenttype', '_sha256')

    @property
    def sha256(self):
        if not self._sha256:
            self._sha256 = sha256(self.datum.encode('utf-8')).hexdigest()
        return self._sha256

    def __init__(self, identifier, datum, datestamp=None, contenttype=None):
        self._sha256 = None
        self.contenttype = contenttype
        self.datestamp = datestamp
        self.datum = datum
        self.identifier = identifier

    def __repr__(self):
        return '<{}({}, {}...)>'.format(self.__class__.__name__, self.identifier, self.sha256[:10])


class BaseHarvester(metaclass=abc.ABCMeta):
    """

    Fetch:
        Aquire and serialize data from a remote source, respecting rate limits.
        fetch* methods return a generator that yield FetchResult objects

    Harvest:
        Fetch and store data, respecting global rate limits.
        harvest* methods return a generator that yield RawDatum objects

    """

    SERIALIZER_CLASS = DeprecatedDefaultSerializer

    network_read_timeout = 30
    network_connect_timeout = 31

    @property
    def request_timeout(self):
        """The timeout tuple for requests (connect, read)
        """
        return (self.network_connect_timeout, self.network_read_timeout)

    def __init__(self, source_config, pretty=False, network_read_timeout=None, network_connect_timeout=None):
        """

        Args:
            source_config (SourceConfig):
            pretty (bool, optional): Defaults to False.

        """
        self.config = source_config
        self.serializer = self.SERIALIZER_CLASS(pretty)

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': settings.SHARE_USER_AGENT})
        # TODO Make rate limit apply across threads
        self.requests = RateLimittedProxy(self.session, self.config.rate_limit_allowance, self.config.rate_limit_period)

        self.network_read_timeout = (network_read_timeout or self.network_read_timeout)
        self.network_connect_timeout = (network_connect_timeout or self.network_connect_timeout)

    def fetch_by_id(self, identifier, **kwargs):
        datum = self._do_fetch_by_id(identifier, **self._get_kwargs(**kwargs))
        return FetchResult(identifier, self.serializer.serialize(datum))

    def _do_fetch_by_id(self, identifier, **kwargs):
        """Fetch a document by provider ID.

        Optional to implement, intended for dev and manual testing.

        Args:
            identifier (str): Unique ID the provider uses to identify works.

        Returns:
            FetchResult

        """
        raise NotImplementedError('{!r} does not support fetching by ID'.format(self))

    def fetch(self, today=False, **kwargs):
        """Fetch data from today.

        Yields:
            FetchResult

        """
        return self.fetch_date_range(datetime.date.today() - datetime.timedelta(days=1), datetime.date.today(), **kwargs)

    def fetch_date(self, date: datetime.date, **kwargs):
        """Fetch data from the specified date.

        Yields:
            FetchResult
        """
        return self.fetch_date_range(date - datetime.timedelta(days=1), date, **kwargs)

    def fetch_date_range(self, start, end, limit=None, **kwargs):
        """Fetch data from the specified date range.

        Yields:
            FetchResult

        """
        if not isinstance(start, datetime.date):
            raise TypeError('start must be a datetime.date. Got {!r}'.format(start))

        if not isinstance(end, datetime.date):
            raise TypeError('end must be a datetime.date. Got {!r}'.format(end))

        if start >= end:
            raise ValueError('start must be before end. {!r} > {!r}'.format(start, end))

        if limit == 0:
            return  # No need to do anything

        # Cast to datetimes for compat reasons
        start = pendulum.instance(datetime.datetime.combine(start, datetime.time(0, 0, 0, 0, timezone.utc)))
        end = pendulum.instance(datetime.datetime.combine(end, datetime.time(0, 0, 0, 0, timezone.utc)))

        if hasattr(self, 'shift_range'):
            warnings.warn(
                '{!r} implements a deprecated interface. '
                'Handle date transforms in _do_fetch. '
                'shift_range will no longer be called in SHARE 2.9.0'.format(self),
                DeprecationWarning
            )
            start, end = self.shift_range(start, end)

        data_gen = self._do_fetch(start, end, **self._get_kwargs(**kwargs))

        if not isinstance(data_gen, types.GeneratorType) and len(data_gen) != 0:
            raise TypeError('{!r}._do_fetch must return a GeneratorType for optimal performance and memory usage'.format(self))

        for i, blob in enumerate(data_gen):
            result = FetchResult(blob[0], self.serializer.serialize(blob[1]), *blob[2:])

            if result.datestamp is None:
                result.datestamp = start
            elif (result.datestamp.date() < start.date() or result.datestamp.date() > end.date()):
                if (start - result.datestamp) > pendulum.Duration(hours=24) or (result.datestamp - end) > pendulum.Duration(hours=24):
                    raise ValueError(
                        'result.datestamp is outside of the requested date range. '
                        '{} from {} is not within [{} - {}]'.format(result.datestamp, result.identifier, start, end)
                    )
                logger.warning(
                    'result.datestamp is within 24 hours of the requested date range. '
                    'This is probably a timezone conversion error and will be accepted. '
                    '{} from {} is within 24 hours of [{} - {}]'.format(result.datestamp, result.identifier, start, end)
                )

            yield result

            if limit is not None and i >= limit:
                break

    def harvest_id(self, identifier, **kwargs):
        """Harvest a document by ID.

        Note:
            Dependent on whether fetch_by_id is implemented.

        Args:
            identifier (str): Unique ID the provider uses to identify works.

        Returns:
            RawDatum

        """
        datum = self.fetch_by_id(identifier, **kwargs)
        return RawDatum.objects.store_data(self.config, datum)

    def harvest(self, **kwargs):
        """Fetch data from yesterday.

        Yields:
            RawDatum

        """
        return self.harvest_date(datetime.date.today(), **kwargs)

    def harvest_date(self, date, **kwargs):
        """Harvest data from the specified date.

        Yields:
            RawDatum

        """
        return self.harvest_date_range(date - datetime.timedelta(days=1), date, **kwargs)

    def harvest_date_range(self, start, end, limit=None, force=False, **kwargs):
        """Fetch data from the specified date range.

        Args:
            start (date):
            end (date):
            limit (int, optional): The maximum number of unique data to harvest. Defaults to None.
                Uniqueness is determined by the SHA-256 of the raw data
            force (bool, optional): Disable all safety checks, unexpected exceptions will still be raised. Defaults to False.
            **kwargs: Forwared to _do_fetch. Overrides values in the source config's harvester_kwargs

        Yields:
            RawDatum

        """
        if self.serializer.pretty:
            raise ValueError('To ensure that data is optimally deduplicated, harvests may not occur while using a pretty serializer.')

        with self.config.acquire_lock(required=not force):
            logger.info('Harvesting %s - %s from %r', start, end, self.config)
            yield from RawDatum.objects.store_chunk(self.config, self.fetch_date_range(start, end, **kwargs), limit=limit)

    def _do_fetch(self, start, end, **kwargs):
        """Fetch date from this source inside of the given date range.

        The given date range should be treated as [start, end)

        Any HTTP[S] requests MUST be sent using the self.requests client.
        It will automatically enforce rate limits

        Args:
            start_date (datetime): Date to start fetching data from, inclusively.
            end_date (datetime): Date to fetch data up to, exclusively.
            **kwargs: Arbitrary kwargs passed to subclasses, used to customize harvesting. Overrides values in the source config's harvester_kwargs.

        Returns:
            Iterator<FetchResult>: The fetched data.

        """
        if hasattr(self, 'do_harvest'):
            warnings.warn(
                '{!r} implements a deprecated interface. '
                'do_harvest has been replaced by _do_fetch for clarity. '
                'do_harvest will no longer be called in SHARE 2.11.0'.format(self),
                DeprecationWarning
            )
            logger.warning('%r implements a deprecated interface. ', self)
            return self.do_harvest(start, end, **kwargs)

        raise NotImplementedError()

    def _get_kwargs(self, **kwargs):
        return {**(self.config.harvester_kwargs or {}), **kwargs}
