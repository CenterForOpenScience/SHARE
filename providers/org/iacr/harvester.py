import logging

from lxml import etree
from share import Harvester

logger = logging.getLogger(__name__)


class IACRHarvester(Harvester):

    namespaces = {
        'ns0': 'http://www.w3.org/2005/Atom'
    }

    url = 'https://eprint.iacr.org/rss/rss.xml'

    def do_harvest(self, start_date, end_date):
        # IACR has previous-search, you can only go from some past day to today
        return self.fetch_records(self.url, start_date)

    def fetch_records(self, url, start_date):
        return self.fetch_page(url)

    def fetch_page(self, url):
        logger.info('Making request to {}'.format(url))

        resp = self.requests.get(url, verify=True)
        parsed = etree.fromstring(resp.content)
        total_records = int(parsed.xpath("//ttl")[0].text)

        records = parsed.xpath('//item', namespaces=self.namespaces)
        logger.info('Found {} records of {}.'.format(len(records), total_records))
        for record in records:
            doc_id = record.xpath('./guid', namespaces=self.namespaces)[0].text
            doc = etree.tostring(record)
            yield (doc_id, doc)