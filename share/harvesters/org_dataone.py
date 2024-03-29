from furl import furl

from lxml import etree

from share.harvest import BaseHarvester


class DataOneHarvester(BaseHarvester):
    VERSION = 1

    def do_harvest(self, start_date, end_date):
        end_date = end_date.format('YYYY-MM-DD') + 'T00:00:00Z'
        start_date = start_date.format('YYYY-MM-DD') + 'T00:00:00Z'

        url = furl(self.config.base_url).set(query_params={
            'q': 'dateModified:[{} TO {}]'.format(start_date, end_date),
            'start': 0,
            'rows': 1
        }).url

        return self.fetch_records(url, start_date, end_date)

    def fetch_records(self, url, start_date, end_date):
        resp = self.requests.get(url)
        doc = etree.XML(resp.content)

        total_records = int(doc.xpath("//result/@numFound")[0])
        records_processed = 0

        while records_processed < total_records:
            response = self.requests.get(furl(url).set(query_params={
                'q': 'dateModified:[{} TO {}]'.format(start_date, end_date),
                'start': records_processed,
                'rows': 1000
            }).url)

            docs = etree.XML(response.content).xpath('//doc')
            for doc in docs:
                doc_id = doc.xpath("str[@name='id']")[0].text
                doc = etree.tostring(doc)
                yield (doc_id, doc)

            records_processed += len(docs)
