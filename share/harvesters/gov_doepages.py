from lxml import etree

from furl import furl

from share.harvest import BaseHarvester


class DoepagesHarvester(BaseHarvester):
    VERSION = 1

    namespaces = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcq': 'http://purl.org/dc/terms/'
    }

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()

        resp = self.requests.get(furl(self.config.base_url).set(query_params={
            'nrows': 1,
            'EntryDateFrom': start_date.strftime('%m/%d/%Y'),
            'EntryDateTo': end_date.strftime('%m/%d/%Y'),
        }).url)

        initial_doc = etree.XML(resp.content)
        num_results = int(initial_doc.xpath('//records/@count', namespaces=self.namespaces)[0])

        records_url = furl(self.config.base_url).set(query_params={
            'nrows': num_results,
            'EntryDateFrom': start_date.strftime('%m/%d/%Y'),
            'EntryDateTo': end_date.strftime('%m/%d/%Y'),
        }).url

        return self.fetch_records(records_url)

    def fetch_records(self, url):
        resp = self.requests.get(url)
        xml = etree.XML(resp.content)
        records = xml.xpath('records/record')

        for record in records:
            doc_id = record.xpath('dc:ostiId/node()', namespaces=self.namespaces)[0]
            doc = etree.tostring(record)
            yield(doc_id, doc)
