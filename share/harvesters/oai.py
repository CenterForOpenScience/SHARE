import logging
import time

import pendulum
from furl import furl
from lxml import etree

from share.harvest import BaseHarvester
from share.harvest.serialization import StringLikeSerializer

logger = logging.getLogger(__name__)


class OAIHarvestException(Exception):
    pass


class OAIHarvester(BaseHarvester):
    VERSION = 1

    namespaces = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ns0': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/',
    }
    SERIALIZER_CLASS = StringLikeSerializer

    def _do_fetch(self, start_date, end_date, metadata_prefix, time_granularity=True, set_spec=None):
        url = furl(self.config.base_url)

        if set_spec:
            url.args['set'] = set_spec
        url.args['verb'] = 'ListRecords'
        url.args['metadataPrefix'] = metadata_prefix

        if time_granularity:
            url.args['from'] = start_date.format('YYYY-MM-DDT00:00:00', formatter='alternative') + 'Z'
            url.args['until'] = end_date.format('YYYY-MM-DDT00:00:00', formatter='alternative') + 'Z'
        else:
            url.args['from'] = start_date.date().isoformat()
            url.args['until'] = end_date.date().isoformat()

        return self.fetch_records(url)

    def fetch_records(self, url: furl) -> list:
        token, used_tokens = None, set()

        while True:
            records, token = self.fetch_page(url, token=token)

            if token in used_tokens:
                raise ValueError('Found duplicate resumption token "{}" from {!r}'.format(token, self))
            used_tokens.add(token)

            for record in records:
                datestamp = record.xpath('ns0:header/ns0:datestamp', namespaces=self.namespaces)[0].text
                if datestamp:
                    datestamp = pendulum.parse(datestamp)
                else:
                    datestamp = None

                yield (
                    record.xpath('ns0:header/ns0:identifier', namespaces=self.namespaces)[0].text,
                    etree.tostring(record, encoding=str),
                    datestamp,
                )

            if not token or not records:
                break

    def fetch_page(self, url: furl, token: str=None) -> (list, str):
        if token:
            url.args = {'resumptionToken': token, 'verb': 'ListRecords'}

        while True:
            logger.info('Making request to {}'.format(url.url))
            resp = self.requests.get(url.url, timeout=self.request_timeout)
            if resp.ok:
                break
            if resp.status_code == 503:
                sleep = int(resp.headers.get('retry-after', 5)) + 2  # additional 2 seconds for good measure
                logger.warning('Server responded with %s. Waiting %s seconds.', resp, sleep)
                time.sleep(sleep)
                continue
            resp.raise_for_status()

        parsed = etree.fromstring(resp.content, parser=etree.XMLParser(recover=True))

        error = parsed.xpath('//ns0:error', namespaces=self.namespaces)
        if error and (len(error) > 1 or error[0].get('code') != 'noRecordsMatch'):
            raise OAIHarvestException(error[0].get('code'), error[0].text)

        records = parsed.xpath('//ns0:record', namespaces=self.namespaces)
        token = (parsed.xpath('//ns0:resumptionToken/node()', namespaces=self.namespaces) + [None])[0]

        logger.info('Found {} records. Continuing with token {}'.format(len(records), token))

        return records, token

    def fetch_by_id(self, identifier, metadata_prefix, **kwargs):
        url = furl(self.config.base_url)
        url.args['verb'] = 'GetRecord'
        url.args['metadataPrefix'] = metadata_prefix
        url.args['identifier'] = identifier
        return etree.tostring(self.fetch_page(url)[0][0], encoding=str)

    def metadata_formats(self):
        url = furl(self.config.base_url)
        url.args['verb'] = 'ListMetadataFormats'
        resp = self.requests.get(url.url, timeout=self.request_timeout)
        resp.raise_for_status()
        parsed = etree.fromstring(resp.content)
        formats = parsed.xpath('//ns0:metadataPrefix', namespaces=self.namespaces)
        return [f.text for f in formats]
