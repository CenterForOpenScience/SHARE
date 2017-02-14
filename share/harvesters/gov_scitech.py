from furl import furl

from lxml import etree

from share.harvest import BaseHarvester


class SciTechHarvester(BaseHarvester):
    KEY = 'gov.scitech'
    VERSION = '0.0.1'

    namespaces = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcq': 'http://purl.org/dc/terms/'
    }

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()

        page = 0
        more_pages = True

        while more_pages:
            response = self.requests.get(furl(self.config.base_url).set(query_params={
                'page': page,
                'EntryDateTo': end_date.strftime('%m/%d/%Y'),
                'EntryDateFrom': start_date.strftime('%m/%d/%Y'),
            }).url)

            xml = etree.XML(response.content)
            records = xml.xpath('records/record')
            for record in records:
                doc_id = record.xpath('dc:ostiId/node()', namespaces=self.namespaces)[0]
                doc = etree.tostring(record)
                yield (doc_id, doc)

            page += 1
            more_pages = xml.xpath('//records/@morepages')[0] == 'true'
