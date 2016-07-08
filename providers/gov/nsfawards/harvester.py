import arrow
import logging

from furl import furl
from typing import Tuple
from typing import Union
from typing import Iterator

from share.harvest.harvester import Harvester

logger = logging.getLogger(__name__)


class NSFAwardsHarvester(Harvester):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = 'http://api.nsf.gov/services/v1/awards.json'


    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:
        url = furl(self.url)

        url.args['dateStart'] = start_date.date().strftime('%m/%d/%Y')
        url.args['dateEnd'] = end_date.date().strftime('%m/%d/%Y')
        url.args['offset'] = 0

        return self.fetch_records(url)

    def fetch_records(self, url: furl) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:
        records = self.requests.get(url.url).json()['response'].get('award')

        total_harvested = 0
        while True:
            for record in records:
                total_harvested += 1
                yield(record['id'], record)

            if len(records) < 25:
                break

            url.args['offset'] += 25
            logger.info('About to harvest {}'.format(url.url))
            records = self.requests.get(url.url).json()['response'].get('award')

        logger.info('Harvested {} records'.format(total_harvested))
