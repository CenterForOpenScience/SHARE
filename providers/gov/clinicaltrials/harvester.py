import time
import logging

from furl import furl

from lxml import etree

from share import Harvester


logger = logging.getLogger(__name__)


class ClinicalTrialsHarvester(Harvester):
    url = 'https://clinicaltrials.gov/ct2/results'

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()

        return self.fetch_records(furl(self.url).set(query_params={
            'displayxml': 'true',
            'lup_s': start_date.strftime('%m/%d/%Y'),
            'lup_e': end_date.strftime('%m/%d/%Y')
        }).url)

    def fetch_records(self, url):
        resp = self.requests.get(url)
        resp_xml = etree.XML(resp.content)
        num_records = int(resp_xml.xpath('//search_results/@count')[0])

        if num_records > 0:
            # create a new URL to request all results
            url = furl(url).add(query_params={
                'count': num_records
            }).url

            all_records_resp = self.requests.get(url)
            all_records_doc = etree.XML(all_records_resp.content)

            # retrieve the URLs for each document to make requests for their full content
            record_urls = [
                furl(record.xpath('url/node()')[0]).set(query_params={
                    'displayxml': 'true'
                }).url
                for record in all_records_doc.xpath('//clinical_study')
            ]

            logger.info("There are {} record urls to harvest - this may take a while...".format(len(record_urls)))
            for url in record_urls:
                try:
                    record_resp = self.requests.get(url)
                except self.requests.exceptions.ConnectionError as e:
                    logger.warning('Connection error: {}, wait a bit...'.format(e))
                    time.sleep(30)
                    record_resp = self.requests.get(url)

                doc = etree.XML(record_resp.content)
                record = etree.tostring(doc)
                doc_id = doc.xpath('//nct_id/node()')[0]
                yield (doc_id, record)
