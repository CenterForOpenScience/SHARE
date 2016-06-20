import logging

from lxml import etree

from share.core import Harvester


logger = logging.getLogger(__name__)


class ArxivHarvester(Harvester):

    rate_limit = (1, 3)  # Rate limit in requests per_second

    URL = 'http://export.arxiv.org/oai2?verb=ListRecords&metadataPrefix=oai_dc&from={}&until={}'
    URL_ = 'http://export.arxiv.org/oai2'

    NAMESPACES = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ns0': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/',
    }

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()

        return self.fetch_records(self.URL.format(start_date.isoformat(), end_date.isoformat()))

    def fetch_records(self, url):
        records = []
        _records, token = self.fetch_page(url, token=None)

        while True:
            records.extend([
                (
                    x.xpath('ns0:header/ns0:identifier', namespaces=self.NAMESPACES)[0].text,
                    etree.tostring(x),
                )
                for x in _records
            ])
            _records, token = self.fetch_page(self.URL_, token=token)

            if not token or not _records:
                break

        return records

    def fetch_page(self, url, token=None):
        if token:
            url += '?resumptionToken={}'.format(token)

        logger.info('Making request to {}'.format(url))

        resp = self.requests.get(url)
        parsed = etree.fromstring(resp.content)

        records = parsed.xpath('//ns0:record', namespaces=self.NAMESPACES)
        token = (parsed.xpath('//ns0:resumptionToken/node()', namespaces=self.NAMESPACES) + [None])[0]

        logger.info('Found {} records. Continuing with token {}'.format(len(records), token))

        return records, token
