import pendulum
from furl import furl

import logging
from share import Harvester

logger = logging.getLogger(__name__)


class PeerJHarvester(Harvester):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = 'https://peerj.com/articles/index.json'
        self.base_preprint_url = 'https://peerj.com/preprints/index.json'

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum):

        return self.fetch_records(self.base_url, start_date, end_date)

    def fetch_records(self, url, start_date, end_date):

        logger.info('Making request to {}'.format(url))
        for url in self.build_url():
            if self.base_preprint_url in url:
                yield from self.fetch_page(url, start_date, end_date, 'preprint-')
            yield from self.fetch_page(url, start_date, end_date)

        logger.info("PeerJ has been harvested")

    def fetch_page(self, url, start_date, end_date, preprint=''):
        while url:
            records = self.requests.get(url).json()

            for record in records['_items']:
                if pendulum.parse(record['date']) < start_date:
                    return

                if pendulum.parse(record['date']) > end_date:
                    continue

                yield (preprint + record['identifiers']['peerj'], record)

            if 'next' in record['_links']:
                url = record['_links']['next']['href']
            else:
                url = None

    def build_url(self):
        return [furl(self.base_url).set(query_params={
            'journal': 'peerj',
        }).url,
            furl(self.base_url).set(query_params={
                'journal': 'cs',
            }).url,
            furl(self.base_preprint_url).set(query_params={
                'journal': 'peerj',
            }).url
        ]
