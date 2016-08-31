import datetime
import logging

from furl import furl
from lxml import etree

from share import Harvester

logger = logging.getLogger(__name__)


class BiorxivHarvester(Harvester):

    namespaces = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'syn': 'http://purl.org/rss/1.0/modules/syndication/',
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'admin': 'http://webns.net/mvcb/',
        'prism': 'http://purl.org/rss/1.0/modules/prism/',
        'taxo': 'http://purl.org/rss/1.0/modules/taxonomy/',
        'ns0': 'http://purl.org/rss/1.0/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    }

    url = 'http://connect.biorxiv.org/biorxiv_xml.php'

    def do_harvest(self, start_date, end_date):
        # BioRxiv does not have filter dates; returns 30 most recent
        start_date = start_date.date()
        url = furl(self.url).set(query_params={
            'subject': 'all'
        }).url
        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(url, start_date)

    def fetch_records(self, url, start_date):
        records = self.fetch_page(url)

        for index, record in enumerate(records):
            # '2016-06-30'
            updated = datetime.datetime.strptime(record.xpath('dc:date', namespaces=self.namespaces)[0].text, '%Y-%m-%d').date()
            if updated < start_date:
                logger.info('Record index {}: Record date {} is less than start date {}.'.format(index, updated, start_date))
                return

            yield (
                record.xpath('dc:identifier', namespaces=self.namespaces)[0].text,
                etree.tostring(record),
            )

    def fetch_page(self, url):
        logger.info('Making request to {}'.format(url))

        resp = self.requests.get(url, verify=False)
        parsed = etree.fromstring(resp.content)

        records = parsed.xpath('//ns0:item', namespaces=self.namespaces)

        logger.info('Found {} records.'.format(len(records)))

        return records
