import abc
import logging

import arrow
from furl import furl
from lxml import etree

from .harvester import Harvester

logger = logging.getLogger(__name__)


class OAIHarvester(Harvester, metaclass=abc.ABCMeta):

    namespaces = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ns0': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/',
    }
    url = None
    time_granularity = True

    def __init__(self, app_config):
        super().__init__(app_config)

        self.url = getattr(self.config, 'url', self.url)
        if not self.url:
            raise NotImplementedError('url')

        self.time_granularity = getattr(self.config, 'time_granularity', self.time_granularity)

    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow) -> list:
        url = furl(self.url)
        url.args['verb'] = 'ListRecords'
        url.args['metadataPrefix'] = 'oai_dc'

        if self.time_granularity:
            url.args['from'] = start_date.format('YYYY-MM-DDT00:00:00') + 'Z'
            url.args['until'] = end_date.format('YYYY-MM-DDT00:00:00') + 'Z'
        else:
            url.args['from'] = start_date.date().isoformat()
            url.args['until'] = end_date.date().isoformat()

        return self.fetch_records(url)

    def fetch_records(self, url: furl) -> list:
        records, token = self.fetch_page(url, token=None)

        while True:
            for record in records:
                yield (
                    record.xpath('ns0:header/ns0:identifier', namespaces=self.namespaces)[0].text,
                    etree.tostring(record),
                )

            records, token = self.fetch_page(url, token=token)

            if not token or not records:
                break

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
