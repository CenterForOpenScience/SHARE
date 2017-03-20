import pendulum
import logging

from furl import furl
from typing import Tuple
from typing import Union
from typing import Iterator

from share.harvest import BaseHarvester

logger = logging.getLogger(__name__)


class NSFAwardsHarvester(BaseHarvester):
    VERSION = '0.0.1'

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:
        url = furl(self.config.base_url)

        url.args['dateStart'] = start_date.date().strftime('%m/%d/%Y')
        url.args['dateEnd'] = end_date.date().strftime('%m/%d/%Y')
        url.args['offset'] = 0

        return self.fetch_records(url)

    def fetch_records(self, url: furl) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:
        while True:
            logger.info('Fetching %s', url.url)
            records = self.requests.get(url.url).json()['response'].get('award', [])

            for record in records:
                yield (record['id'], record)

            if len(records) < 25:
                break

            url.args['offset'] += 25
