import abc
import json
import time
import logging
import datetime
from collections import OrderedDict

import arrow
from furl import furl
import requests
from lxml import etree

from django.db import transaction
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


class Harvester(metaclass=abc.ABCMeta):

    # TODO Make this apply across threads
    rate_limit = (5, 1)  # Rate limit in requests per_second

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
        return self.config.as_source()

    def __init__(self, app_config):
        self.last_call = 0
        self.config = app_config
        self.allowance = self.rate_limit[0]

    @abc.abstractmethod
    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow) -> list:
        """Fetch date from this provider inside of the given date range.

        Any HTTP[S] requests MUST be sent using the self.requests client.
        It will automatically in force rate limits

        Args:
            start_date (datetime):
            end_date (datetime):

        Returns:
            List<Tuple<str, str|dict|bytes>>: The fetched data paired with
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

    def harvest(self, start_date: [datetime.datetime, datetime.timedelta, arrow.Arrow]=None, end_date: [datetime.datetime, datetime.timedelta, arrow.Arrow]=None, shift_range: bool=True) -> list:
        from share.models import RawData
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

        return stored

    def encode_json(self, data: dict) -> str:
        """Orders a python dict recursively so it will always hash to the
        same value. Used for Dedupping harvest results
        Args:
            data (dict):

        Returns:
            str: json.dumpsed ordered dictionary
        """
        def order_json(data: dict) -> OrderedDict:
            return OrderedDict(sorted([
                (key, order_json(value) if isinstance(value, dict) else value)
                for key, value in data.items()
            ], key=lambda x: x[0]))
        return json.dumps(order_json(data)).encode()


class OAIHarvester(Harvester, metaclass=abc.ABCMeta):

    time_granularity = False
    namespaces = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ns0': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/',
    }

    @abc.abstractproperty
    def url(self) -> str:
        raise NotImplementedError

    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow) -> list:
        url = furl(self.url)
        url.args['verb'] = 'ListRecords'
        url.args['metadataPrefix'] = 'oai_dc'

        if self.time_granularity:
            url.args['from'] = start_date.isoformat()
            url.args['until'] = end_date.isoformat()
        else:
            url.args['from'] = start_date.date().isoformat()
            url.args['until'] = end_date.date().isoformat()

        return self.fetch_records(url)

    def fetch_records(self, url: furl) -> list:
        records = []
        _records, token = self.fetch_page(url, token=None)

        while True:
            records.extend([
                (
                    x.xpath('ns0:header/ns0:identifier', namespaces=self.namespaces)[0].text,
                    etree.tostring(x),
                )
                for x in _records
            ])
            _records, token = self.fetch_page(url, token=token)

            if not token or not _records:
                break

        return records

    def fetch_page(self, url: furl, token: str=None) -> (list, str):
        if token:
            url.remove('from')
            url.remove('until')
            url.remove('metadataPrefix')
            url.args['resumptionToken'] = token

        logger.info('Making request to {}'.format(url.url))

        resp = self.requests.get(url.url)
        parsed = etree.fromstring(resp.content)

        records = parsed.xpath('//ns0:record', namespaces=self.namespaces)
        token = (parsed.xpath('//ns0:resumptionToken/node()', namespaces=self.namespaces) + [None])[0]

        logger.info('Found {} records. Continuing with token {}'.format(len(records), token))

        return records, token
