import datetime
import logging
import re

from furl import furl
from lxml import etree
from bs4 import BeautifulSoup

from share import Harvester

logger = logging.getLogger(__name__)


class BiorxivHarvester(Harvester):

    # http://biorxiv.org/archive?field_highwire_a_epubdate_value[value][year]=2016&field_highwire_a_epubdate_value[value][month]=1&page=1

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

    url = 'http://biorxiv.org/search/'

    # limit_from%3A2016-01-23%20limit_to%3A2016-01-31%20numresults%3A100%20sort%3Arelevance-rank%20format_result%3Astandard

    def do_harvest(self, start_date, end_date):

        start_date = start_date.date()
        end_date = end_date.date()
        # get the start year and month for the url
        # import ipdb; ipdb.set_trace()

        # pages start from 0
        url = furl(self.url).set(query_params={
            'limit_from': '2016-01-23',
            'limit_to': '2016-01-31',
            'numresults': '100',
            'format_result': 'standard'
        }).url
        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(url, start_date, end_date)

    def fetch_records(self, url, start_date, end_date):
        resp = self.requests.get(url)
        records = BeautifulSoup(resp.content, 'html.parser')

        import ipdb; ipdb.set_trace()

        # regex for href = content/early
        article_list = re.findall('href = \/content\/early', str(records.find('body')))

        for article in enumerate(article_list):

            # get the header from each url
            record = self.requests.get(article)

            metadata = []
            soup = BeautifulSoup(record.content, 'html.parser')
            head = soup.head.find_all(lambda tag: tag.name == 'meta' or tag.name == 'link')

            # 'check to see if the citation date is past the end date'
            for tag in head:
                if 'name' in tag.attrs and tag.attrs['name'] == 'DC.date':
                    if arrow.get(tag.attrs['content'], 'YYYY-MM-DD HH:mm:ss') < start_date:
                        logger.info('Record index {}: Record date {} is less than start date {}.'.format(index, tag.attrs['content'], start_date))
                        return

                    # is this necessary?
                    if arrow.get(tag.attrs['content'], 'YYYY-MM-DD HH:mm:ss') > end_date:
                        continue

                metadata.append(tag.attrs)

            yield (
                record.xpath('DC.Identifier', namespaces=self.namespaces)[0].text,
                etree.tostring(record),
            )

    def increment_url(self, url):

        return furl(self.url).set(query_params={
            'field_highwire_a_epubdate_value[value][year]': '2016',
            'field_highwire_a_epubdate_value[value][month]': '1',
            'page': '0'
        }).url
