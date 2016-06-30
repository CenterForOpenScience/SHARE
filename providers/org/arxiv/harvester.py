import logging
import datetime

from furl import furl
from lxml import etree

from share import Harvester

logger = logging.getLogger(__name__)


class ArxivHarvester(Harvester):

    namespaces = {
        'ns0': 'http://www.w3.org/2005/Atom'
    }

    url = 'https://export.arxiv.org/api/query'

    def __init__(self, app_config):
        super().__init__
        self.start_page_num = 0

    def get_next_url(self):
        return (furl(self.url).set(query_params={
            'search_query': 'all',
            'max_results': '100',
            'sortBy': 'lastUpdatedDate',
            'sortOrder': 'descending',
            'start': self.start_page_num
        }).url)

    def do_harvest(self, start_date, end_date):
        # Arxiv does not have filter dates; can sort by last updated
        start_date = start_date.date()
        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(self.url, start_date)

    def fetch_records(self, url, start_date):
        records = self.fetch_page(self.get_next_url())

        while True:
            for index, record in enumerate(records):
                # '2016-06-28T19:54:40Z'
                updated = datetime.datetime.strptime(record.xpath('ns0:updated', namespaces=self.namespaces)[0].text, '%Y-%m-%dT%H:%M:%SZ').date()
                if updated < start_date:
                    logger.info('Record index {}: Updated record date {} is less than start date {}.'.format(index, updated, start_date))
                    return

                yield (
                    record.xpath('ns0:id', namespaces=self.namespaces)[0].text,
                    etree.tostring(record),
                )

            self.start_page_num += 100
            records = self.fetch_page(self.get_next_url())

            if not records:
                break

    def fetch_page(self, url):
        logger.info('Making request to {}'.format(url))

        resp = self.requests.get(url, verify=False)
        parsed = etree.fromstring(resp.content)

        records = parsed.xpath('//ns0:entry', namespaces=self.namespaces)

        logger.info('Found {} records.'.format(len(records)))

        return records
