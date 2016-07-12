import arrow
from furl import furl

import logging

from share import Harvester

logger = logging.getLogger(__name__)


class PeerJHarvester(Harvester):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = 'https://peerj.com/articles/index.json/'

    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow):

        return self.fetch_records(start_date, self.base_url, end_date)

    def fetch_records(self, url, start_date, end_date):

        logger.info('Making request to {}'.format(url))
        records = self.requests.get(url).json()
        next_page = records.get('next')

        for record in records['_items']:
            if arrow.get(record['date']) < start_date:
                break

            if arrow.get(record['date']) > end_date:
                continue

            yield (record['identifiers']['peerj'], record)

        else:
            if next_page:
                self.fetch_records(next_page, start_date, end_date)

        logger.info("PeerJ has been harvested.")
