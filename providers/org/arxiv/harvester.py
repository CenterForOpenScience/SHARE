import logging

from furl import furl
from lxml import etree

from share import Harvester

logger = logging.getLogger(__name__)


class ArxivHarvester(Harvester):
    namespaces = {
        'ns0': 'http://www.w3.org/2005/Atom'
    }
    url = 'http://export.arxiv.org/api/query?search_query=all'

    def do_harvest(self, start_date, end_date):
        # Arxiv does not have dates

        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(self.url)

    def fetch_records(self, url):
        records = self.fetch_page(furl(url))

        for record in records:
            yield (
                record.xpath('ns0:id', namespaces=self.namespaces)[0].text,
                etree.tostring(record),
            )

    def fetch_page(self, url):
        logger.info('Making request to {}'.format(url.url))

        resp = self.requests.get(url.url)
        parsed = etree.fromstring(resp.content)

        records = parsed.xpath('//ns0:entry', namespaces=self.namespaces)

        logger.info('Found {} records.'.format(len(records)))

        return records
