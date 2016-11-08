import logging
from typing import Tuple
from typing import Union
from typing import Iterator

import pendulum
from furl import furl

from share.harvest.harvester import Harvester

logger = logging.getLogger(__name__)

QA_TAG = 'qatest'


class OSFHarvester(Harvester):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = 'https://api.osf.io/v2/nodes/'

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:

        url = furl(self.url)

        url.args['page[size]'] = 100
        url.args['filter[public]'] = 'true'
        url.args['embed'] = 'affiliated_institutions'
        url.args['filter[date_modified][gt]'] = start_date.date().isoformat()
        url.args['filter[date_modified][lt]'] = end_date.date().isoformat()
        url.args['filter[preprint][eq]'] = 'false'

        return self.fetch_records(url)

    def fetch_records(self, url: furl) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:
        records, next_page = self.fetch_page(url)
        total_records = records.json()['links']['meta']['total']

        total_harvested = 0
        while True:
            for record in records.json()['data']:
                if QA_TAG in record['attributes']['tags']:
                    continue

                # iterate the linked contributors data in a new key in the record
                contributor_url = furl(record['relationships']['contributors']['links']['related']['href'])
                contributor_url.args['page[size]'] = 100
                contributor_records, next_contributor_page = self.fetch_page(contributor_url)
                total_contributors = contributor_records.json()['links']['meta']['total']
                contributor_data = []
                while True:
                    contributor_data = contributor_data + contributor_records.json()['data']
                    if not next_contributor_page:
                        break
                    contributor_records, next_contributor_page = self.fetch_page(next_contributor_page)
                logger.info('Had {} contributors to harvest, harvested {}'.format(total_contributors, len(contributor_data)))
                record['contributors'] = contributor_data

                # gather the the rest of the record
                total_harvested += 1
                yield (record['id'], record)

            if not next_page:
                break
            records, next_page = self.fetch_page(next_page)

        logger.info('Had {} records to harvest, harvested {}'.format(total_records, total_harvested))

    def fetch_page(self, url: furl, next_page: str=None) -> (list, str):
        logger.info('Making request to {}'.format(url.url))

        records = self.requests.get(url.url)
        next_page = records.json()['links'].get('next')
        next_page = furl(next_page) if next_page else None

        logger.info('Found {} records.'.format(len(records.json()['data'])))

        return records, next_page
