from furl import furl
from lxml import etree

from django.conf import settings

from share import Harvester


class PLOSHarvester(Harvester):

    url = 'http://api.plos.org/search'
    MAX_ROWS_PER_REQUEST = 999

    def do_harvest(self, start_date, end_date):

        if not settings.PLOS_API_KEY:
            raise Exception('PLOS api key not defined.')

        start_date = start_date.isoformat().split('.')[0] + 'Z'
        end_date = end_date.isoformat().split('.')[0] + 'Z'

        return self.fetch_rows(furl(self.url).set(query_params={
            'q': 'publication_date:[{} TO {}]'.format(start_date, end_date),
            'rows': '0',
            'api_key': settings.PLOS_API_KEY
        }).url, start_date, end_date)

    def fetch_rows(self, url, start_date, end_date):
        resp = self.requests.get(url)

        total_rows = etree.XML(resp.content).xpath('//result/@numFound')
        total_rows = int(total_rows[0]) if total_rows else 0

        current_row = 0
        while current_row < total_rows:
            response = self.requests.get(furl(self.url).set(query_params={
                'q': 'publication_date:[{} TO {}]'.format(start_date, end_date),
                'start': current_row,
                'api_key': settings.PLOS_API_KEY,
                'rows': self.MAX_ROWS_PER_REQUEST
            }).url)

            docs = etree.XML(response.content).xpath('//doc')
            for doc in docs:
                if doc.xpath("arr[@name='abstract']") or doc.xpath("str[@name='author_display']"):
                    doc_id = doc.xpath("str[@name='id']")[0].text
                    doc = etree.tostring(doc)
                    yield (doc_id, doc)

            current_row += len(docs)
