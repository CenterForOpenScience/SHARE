import arrow
import logging

from furl import furl
from typing import Tuple
from typing import Union
from typing import Iterator

from share.harvest.harvester import Harvester

logger = logging.getLogger(__name__)


class OSFHarvester(Harvester):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = 'https://api.osf.io/v2/nodes/?page[size]=100&filter[public]=true&embed=affiliated_institutions'

    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:

        url = furl(self.url)

        url.args['filter[date_modified][gt]'] = start_date.date().isoformat()
        url.args['filter[date_modified][lt]'] = end_date.date().isoformat()

        return self.fetch_records(url)

    def fetch_records(self, url: furl) -> list:
        records, next_page = self.fetch_page(url)
        total_records = records.json()['links']['meta']['total']

        total_harvested = 0
        while True:
            for record in records.json()['data']:

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
                yield(record['id'], record)

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
