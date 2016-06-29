from furl import furl
from lxml import etree

from project.settings import PLOS_API_KEY

from share import Harvester


class PLOSHarvester(Harvester):

    url = 'http://api.plos.org/search'
    MAX_ROWS_PER_REQUEST = 999

    def do_harvest(self, start_date, end_date):
        start_date = start_date.date()
        end_date = end_date.date()

        return self.fetch_rows(furl(self.url).set(query_params={
            'q': 'publication_date:[{}T00:00:00Z TO {}T23:59:59Z]'.format(start_date.isoformat(), end_date.isoformat()),
            'rows': '0',
            'api_key': PLOS_API_KEY
        }).url, start_date, end_date)

    def fetch_rows(self, url, start_date, end_date):

        resp = self.requests.get(url)

        total_rows = etree.XML(resp.content).xpath('//result/@numFound')
        total_rows = int(total_rows[0]) if total_rows else 0

        current_row = 0
        while current_row < total_rows:
            response = self.requests.get(furl(self.url).set(query_params={
                'q': 'publication_date:[{}T00:00:00Z TO {}T23:59:59Z]'.format(start_date.isoformat(), end_date.isoformat()),
                'start': current_row,
                'api_key': PLOS_API_KEY,
                'rows': self.MAX_ROWS_PER_REQUEST
            }).url)

            for doc in etree.XML(response.content).xpath('//doc'):
                if doc.xpath("arr[@name='abstract']") or doc.xpath("str[@name='author_display']"):
                    doc_id = doc.xpath("str[@name='id']")[0].text
                    doc = etree.tostring(doc)
                    yield (doc_id, doc)

            current_row += self.MAX_ROWS_PER_REQUEST
