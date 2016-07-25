import datetime
import logging

from furl import furl
from lxml import etree
import requests
from share import Harvester
from io import StringIO, BytesIO

logger = logging.getLogger(__name__)

class IACRHarvester(Harvester):

    namespaces = {
        'ns0': 'http://www.w3.org/2005/Atom'
    }

    url = 'http://eprint.iacr.org/rss/rss.xml'

    def do_harvest(self, start_date, end_date):
        # IACR has previous-search, you can only go from some past day to today
        date_format = "%Y-%m-%d"
        d0 = start_date.date()
        d1 = datetime.date.today()
        delta = d1 - d0
        start_date = start_date.date()
        url = furl(self.url).set(query_params={
            'last': delta.days,
            'title': '1'
        }).url
        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(self.url, start_date)

    def fetch_records(self, url, start_date):
        records = self.fetch_page(url)

        for index, record in enumerate(records):
            # '2016-06-30'
            # updated = datetime.datetime.strptime(record.xpath('dc:date', namespaces=self.namespaces)[0].text, '%Y-%m-%d').date()
            #if updated < start_date:
            #    logger.info('Record index {}: Record date {} is less than start date {}.'.format(index, updated, start_date))
            #    return

            yield (
                record['link'],
                record
            )

    def fetch_page(self, url):
        logger.info('Making request to {}'.format(url))
        data = []
        resp = self.requests.get(url, verify=False)
        # print(resp.content)
        parser = etree.HTMLParser()
        # parsed = etree.parse(BytesIO(resp.content))
        parsed = etree.fromstring(resp.content)
        # result = etree.tostring(parsed.getroot(), pretty_print=True, method="html")
        records = parsed.xpath('//item', namespaces=self.namespaces)

        logger.info('Found {} records.'.format(len(records)))
        for record in records:
            title, authors = record[1].text.split(', by')
            data.append({'link':record[0].text, 'description': record[2].text, 'title':title.strip(),'authors':[a.strip(' ') for a in authors.split('and')] })
        return data

    # def fetch_records(self, url):
    #     resp = self.requests.get(url)
    #     xml = etree.XML(resp.content)
    #     records = xml.xpath('records/record', namespaces=self.namespaces)
    #     print(resp.content)
    #     print(xml)
    #     print(records)
    #
    #     for record in records:
    #         doc_id = record.xpath('dc:ostiId/node()', namespaces=self.namespaces)[0]
    #         doc = etree.tostring(record)
    #         yield(doc_id, doc)
