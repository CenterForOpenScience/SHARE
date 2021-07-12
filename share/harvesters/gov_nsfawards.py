import pendulum
import logging

from furl import furl
from typing import Tuple
from typing import Union
from typing import Iterator

from share.harvest import BaseHarvester

logger = logging.getLogger(__name__)


PAGE_SIZE = 25

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

    def shift_range(self, start_date: pendulum.DateTime, end_date: pendulum.DateTime) -> Tuple[pendulum.DateTime, pendulum.DateTime]:
        # HACK: Records are made available one business day *after* their "date".
        # Accounting for holidays, they might be delayed over a 4-day weekend.
        # When harvesting yesterday's data, actually reach back farther...
        if end_date.is_today():
            start_date = start_date.subtract(days=5)
        return start_date, end_date

    def _do_fetch(self, start_date: pendulum.DateTime, end_date: pendulum.DateTime) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:
        url = furl(self.config.base_url)

        url.args['dateStart'] = start_date.date().strftime('%m/%d/%Y')
        url.args['dateEnd'] = end_date.date().strftime('%m/%d/%Y')
        url.args['offset'] = 0
        url.args['printFields'] = ','.join(NSF_FIELDS)
        url.args['rpp'] = PAGE_SIZE

        return self.fetch_records(url)

    def fetch_records(self, url: furl) -> Iterator[Tuple[str, Union[str, dict, bytes], pendulum.DateTime]]:
        while True:
            logger.info('Fetching %s', url.url)
            records = self.requests.get(url.url).json()['response'].get('award', [])

            for record in records:
                yield (record['id'], record, pendulum.from_format(record['date'], '%m/%d/%Y'))

            if len(records) < PAGE_SIZE:
                break

            url.args['offset'] += PAGE_SIZE
