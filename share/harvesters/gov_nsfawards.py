import pendulum
import logging

from furl import furl
from typing import Tuple
from typing import Union
from typing import Iterator

from share.harvest import BaseHarvester

logger = logging.getLogger(__name__)


NSF_FIELDS = [
    'id',
    'agency',
    'awardeeCity',
    'awardeeCountryCode',
    'awardeeCounty',
    'awardeeDistrictCode',
    'awardeeName',
    'awardeeStateCode',
    'awardeeZipCode',
    'cfdaNumber',
    'coPDPI',
    'date',
    'startDate',
    'expDate',
    'estimatedTotalAmt',
    'fundsObligatedAmt',
    'dunsNumber',
    'fundProgramName',
    'parentDunsNumber',
    'pdPIName',
    'perfCity',
    'perfCountryCode',
    'perfCounty',
    'perfDistrictCode',
    'perfLocation',
    'perfStateCode',
    'perfZipCode',
    'poName',
    'primaryProgram',
    'transType',
    'title',
    'awardee',
    'poPhone',
    'poEmail',
    'awardeeAddress',
    'perfAddress',
    'publicationResearch',
    'publicationConference',
    'fundAgencyCode',
    'awardAgencyCode',
    'projectOutComesReport',
    'abstractText',
    'piFirstName',
    'piMiddeInitial',
    'piLastName',
    'piPhone',
    'piEmail'
]


class NSFAwardsHarvester(BaseHarvester):
    VERSION = 2

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:
        url = furl(self.config.base_url)

        url.args['dateStart'] = start_date.date().strftime('%m/%d/%Y')
        url.args['dateEnd'] = end_date.date().strftime('%m/%d/%Y')
        url.args['offset'] = 0
        url.args['printFields'] = ','.join(NSF_FIELDS)

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
