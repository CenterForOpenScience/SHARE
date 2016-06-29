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
    start_page_num = 0
    url = 'http://export.arxiv.org/api/query?search_query=all&max_results=100&sortBy=lastUpdatedDate&sortOrder=descending'

    def get_next_url(self):
        self.start_page_num += 100
        return self.url + '&start={}'.format(self.start_page_num)

    def do_harvest(self, start_date, end_date):
        # Arxiv does not have filter dates; can sort by last updated
        start_date = start_date.date()
        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(self.url, start_date)

    def fetch_records(self, url, start_date):
        records = self.fetch_page(furl(url))

        while True:
            # '2016-06-28T19:54:40Z'
            updated = datetime.datetime.strptime(records[0].xpath('ns0:updated', namespaces=self.namespaces)[0].text, '%Y-%m-%dT%H:%M:%SZ').date()
            for record in records:

                yield (
                    record.xpath('ns0:id', namespaces=self.namespaces)[0].text,
                    etree.tostring(record),
                )

            if updated < start_date:
                logger.info('Updated record date {} is less than start date {}.'.format(updated, start_date))
                break

            records = self.fetch_page(furl(self.get_next_url()))

            if not records:
                break

    def fetch_page(self, url):
        logger.info('Making request to {}'.format(url.url))

        resp = self.requests.get(url.url)
        parsed = etree.fromstring(resp.content)

        records = parsed.xpath('//ns0:entry', namespaces=self.namespaces)

        logger.info('Found {} records.'.format(len(records)))

        return records
