import logging
from typing import Tuple
from typing import Union
from typing import Iterator

import arrow
from furl import furl

from providers.io.osf.harvester import OSFHarvester

logger = logging.getLogger(__name__)


class SocarxivHarvester(OSFHarvester):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = 'http://staging2-api.osf.io/v2/preprints/'

    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:

        url = furl(self.url)

        url.args['filter[provider]'] = 'socarxiv'
        url.args['page[size]'] = 100
        url.args['filter[date_modified][gt]'] = start_date.date().isoformat()
        url.args['filter[date_modified][lt]'] = end_date.date().isoformat()

        return self.fetch_records(url)
