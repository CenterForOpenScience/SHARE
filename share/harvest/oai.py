import time
import logging

import pendulum
from furl import furl
from lxml import etree

from .base import BaseHarvester

logger = logging.getLogger(__name__)


class OAIHarvester(BaseHarvester):
    KEY = 'oai'
    VERSION = '0.0.1'

    namespaces = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ns0': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/',
    }
    time_granularity = True
    from_param = 'from'
    until_param = 'until'

    def __init__(self, source, metadata_prefix, **kwargs):
        super().__init__(source, **kwargs)

        self.url = source.base_url
        self.metadata_prefix = metadata_prefix
        self.time_granularity = kwargs.get('time_granularity', self.time_granularity)
        self.from_param = kwargs.get('from_param', self.from_param)
        self.until_param = kwargs.get('until_param', self.until_param)

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum, set_spec=None) -> list:
        url = furl(self.url)

        if set_spec:
            url.args['set'] = set_spec
        url.args['verb'] = 'ListRecords'
        url.args['metadataPrefix'] = self.metadata_prefix

        if self.time_granularity:
            url.args[self.from_param] = start_date.format('YYYY-MM-DDT00:00:00', formatter='alternative') + 'Z'
            url.args[self.until_param] = end_date.format('YYYY-MM-DDT00:00:00', formatter='alternative') + 'Z'
        else:
            url.args[self.from_param] = start_date.date().isoformat()
            url.args[self.until_param] = end_date.date().isoformat()

        return self.fetch_records(url)

    def fetch_records(self, url: furl) -> list:
        token = None

        while True:
            records, token = self.fetch_page(url, token=token)
            for record in records:
                yield (
                    record.xpath('ns0:header/ns0:identifier', namespaces=self.namespaces)[0].text,
                    etree.tostring(record),
                )

            if not token or not records:
                break

    def fetch_page(self, url: furl, token: str=None) -> (list, str):
        if token:
            url.args = {'resumptionToken': token, 'verb': 'ListRecords'}

        while True:
            logger.info('Making request to {}'.format(url.url))
            resp = self.requests.get(url.url)
            if resp.ok:
                break
            if resp.status_code == 503:
                sleep = int(resp.headers.get('retry-after', 5)) + 2  # additional 2 seconds for good measure
                logger.warning('Server responded with %s. Waiting %s seconds.', resp, sleep)
                time.sleep(sleep)
                continue
            resp.raise_for_status()

        parsed = etree.fromstring(resp.content)

        records = parsed.xpath('//ns0:record', namespaces=self.namespaces)
        token = (parsed.xpath('//ns0:resumptionToken/node()', namespaces=self.namespaces) + [None])[0]

        logger.info('Found {} records. Continuing with token {}'.format(len(records), token))

        return records, token

    def fetch_by_id(self, provider_id):
        url = furl(self.url)
        url.args['verb'] = 'GetRecord'
        url.args['metadataPrefix'] = self.metadata_prefix
        url.args['identifier'] = provider_id
        return etree.tostring(self.fetch_page(url)[0][0])
