import datetime
import logging

from furl import furl
from lxml import etree
import requests
from share import Harvester
from html.parser import HTMLParser
from io import StringIO, BytesIO

# from .eprint_parser import EPrintParser

logger = logging.getLogger(__name__)
def new_or_revised(pub_id):
    HTTP_HEADERS = {
        "Accept":          "text/html,application/xhtml+xml,application/xml;"
                           + "q=0.9,*/*;q=0.8",
        "Accept-Language": "en-us,en;q=0.5",
        "Accept-Encoding": "deflate",
        "Accept-Charset":  "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
        "Connection":      "keep-alive",
        "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; "
                           + "rv:7.0.1) Gecko/20100101 Firefox/7.0.1",
    }
    resp = requests.get(
        'http://eprint.iacr.org/eprint-bin/versions.pl?entry=' + pub_id,
        headers=HTTP_HEADERS
    )

    if resp.status_code != 200:
        # try again
        resp = requests.get(
            'http://eprint.iacr.org/eprint-bin/versions.pl?entry=' + pub_id,
            headers=HTTP_HEADERS
        )

    if resp.status_code != 200:
        raise Exception(
            'new_or_revised request (' + pub_id + 'error: ' + resp.status_code
            + '\n\n' + resp.text)

    if resp.text.count('posted') > 1:
        return 'revised'
    else:
        return 'new'

class EPrintParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.in_main_content = False
        self.data_type = None
        self.entry = None
        self.list_entries = []

    def feed(self, data):
        HTMLParser.feed(self, data)
        return self.list_entries

    def handle_starttag(self, tag, attrs):
        if tag == 'dl':
            self.in_main_content = True
            return

        if not self.in_main_content:
            return

        if tag == 'dt':
            if self.entry:
                self.list_entries.append(self.entry)
            self.entry = dict()
        elif tag == 'a':
            self.data_type = 'link'
        elif tag == 'b':
            self.data_type = 'title'
        elif tag == 'em':
            self.data_type = 'authors'

    def handle_endtag(self, tag):
        if tag == 'dl':
            self.in_main_content = False

            if self.entry:
                self.list_entries.append(self.entry)
                self.entry = None

            assert self.data_type is None

        elif tag in ('a', 'em', 'b'):
            self.data_type = None

    def handle_data(self, data):
        if not self.in_main_content:
            return

        if data in ('PDF', 'PS', 'PS.GZ') and self.data_type == 'link':
            # self.entry['update_type'] = \
            #    new_or_revised(self.entry['pub_id'])
            return

        elif 'withdrawn' in data and self.data_type is None:
            self.entry['update_type'] = 'withdrawn'
            return

        if self.data_type == 'link':
            self.entry['pub_id'] = data
        elif self.data_type:
            if self.data_type in self.entry:
                self.entry[self.data_type] += data
            else:
                self.entry[self.data_type] = data

    def handle_charref(self, data):
        data = '&#' + data + ';'
        if self.data_type:
            if self.data_type in self.entry:
                self.entry[self.data_type] += HTMLParser().unescape(data)
            else:
                self.entry[self.data_type] = HTMLParser().unescape(data)

class IACRHarvester(Harvester):

    namespaces = {
        'ns0': 'http://purl.org/rss/1.0/'
    }

    url = 'http://eprint.iacr.org/eprint-bin/search.pl?'

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
        return self.fetch_records(url, start_date)

    def fetch_records(self, url, start_date):
        records = self.fetch_page(url)

        for index, record in enumerate(records):
            # '2016-06-30'
            # updated = datetime.datetime.strptime(record.xpath('dc:date', namespaces=self.namespaces)[0].text, '%Y-%m-%d').date()
            #if updated < start_date:
            #    logger.info('Record index {}: Record date {} is less than start date {}.'.format(index, updated, start_date))
            #    return

            yield (
                record['pub_id'],
                record
            )

    def fetch_page(self, url):
        logger.info('Making request to {}'.format(url))

        resp = self.requests.get(url, verify=False)
        # print(resp.content)
        parser = etree.HTMLParser()
        parsed = etree.parse(BytesIO(resp.content), parser)
        result = etree.tostring(parsed.getroot(), pretty_print=True, method="html")
        records = parsed.xpath('//ns0:item', namespaces=self.namespaces)
        myparser = EPrintParser()
        entries = myparser.feed(resp.text)
        logger.info('Found {} records.'.format(len(records)))

        return entries

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
