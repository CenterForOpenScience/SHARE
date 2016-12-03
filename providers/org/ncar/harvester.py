import logging

from furl import furl
from lxml import etree

from share.harvest.harvester import Harvester

logger = logging.getLogger(__name__)


class NCARHarvester(Harvester):

    namespaces = {
        'OAI-PMH': 'http://www.openarchives.org/OAI/2.0/',
        'dif': 'http://gcmd.gsfc.nasa.gov/Aboutus/xml/dif/'
    }
    url = 'https://www.earthsystemgrid.org/oai/repository'

    def do_harvest(self, start_date, end_date):
        url = furl(self.url).set(query_params={
            'verb': 'ListRecords',
            'metadataPrefix': 'dif',
            'from': start_date.format('YYYY-MM-DDT00:00:00', formatter='alternative') + 'Z',
            'until': end_date.format('YYYY-MM-DDT00:00:00', formatter='alternative') + 'Z'
        })

        return self.fetch_records(url)

    def fetch_records(self, url):
        records, token = self.fetch_page(url, token=None)

        while True:
            for record in records:
                yield (
                    record.xpath('./OAI-PMH:header/OAI-PMH:identifier/node()', namespaces=self.namespaces)[0],
                    etree.tostring(record),
                )

            records, token = self.fetch_page(url, token=token)

            if not token or not records:
                break

    def fetch_page(self, url, token):
        if token:
            url.remove('from')
            url.remove('until')
            url.remove('metadataPrefix')
            url.args['resumptionToken'] = token

        logger.info('Making request to {}'.format(url))

        resp = self.requests.get(url.url)
        parsed = etree.fromstring(resp.content)

        records = parsed.xpath('//OAI-PMH:record', namespaces=self.namespaces)
        token = (parsed.xpath('//OAI-PMH:resumptionToken/node()', namespaces=self.namespaces) + [None])[0]

        logger.info('Found {} records. Continuing with token {}'.format(len(records), token))

        return records, token
