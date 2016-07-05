import logging
from typing import Tuple
from typing import Union
from typing import Iterator

import arrow
from furl import furl

from providers.io.osf.harvester import OSFHarvester

logger = logging.getLogger(__name__)



class OSFRegistrationsHarvester(OSFHarvester):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = 'https://api.osf.io/v2/registrations/'


    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:

        url = furl(self.url)

        url.args['page[size]'] = 100
        url.args['filter[public]'] = 'true'
        url.args['embed'] = 'affiliated_institutions'
        url.args['embed'] = 'identifiers'
        url.args['filter[date_created][gt]'] = start_date.date().isoformat()
        url.args['filter[date_created][lt]'] = end_date.date().isoformat()

        return self.fetch_records(url)
