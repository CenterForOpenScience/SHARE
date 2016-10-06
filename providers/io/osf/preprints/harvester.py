import logging
import datetime
from typing import Tuple
from typing import Union
from typing import Iterator

import pendulum
from furl import furl
from django.conf import settings

from providers.io.osf.harvester import OSFHarvester

logger = logging.getLogger(__name__)


class PreprintHarvester(OSFHarvester):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = '{}v2/preprint_providers/osf/preprints/'.format(settings.OSF_API_URL)

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:

        url = furl(self.url)

        url.args['page[size]'] = 100
        # OSF turns dates into date @ midnight so we have to go ahead one more day
        url.args['filter[date_modified][gte]'] = start_date.date().isoformat()
        url.args['filter[date_modified][lte]'] = (end_date + datetime.timedelta(days=2)).date().isoformat()

        return self.fetch_records(url)
