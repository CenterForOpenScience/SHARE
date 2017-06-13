import csv
import datetime

import logging

from share.harvest import BaseHarvester

logger = logging.getLogger(__name__)


class SCHarvester(BaseHarvester):
    """
    """
    VERSION = 1

    def _do_fetch(self, start, end, **kwargs):
        end_date = end.date()
        start_date = start.date()
        logger.info('Harvesting the social science registry %s - %s', start_date, end_date)
        return self.fetch_records(start_date, end_date)

    def fetch_records(self, start_date, end_date):

        csv_response = self.requests.get(self.kwargs['csv_url'])

        csv_response.raise_for_status()

        decoded_content = csv_response.content.decode('utf-8')

        cr = csv.reader(decoded_content.splitlines(), delimiter=',')
        record_list = list(cr)
        record_list = record_list[1:]
        total_records = len(record_list)

        logging.info('Found total %d results from the social science registry', total_records)
        standard_size = 41
        records_ignored = 0
        records_harvested = 0

        for i, record in enumerate(record_list):
            logger.info('On trial %d of %d (%d%%)', i, total_records, (i / total_records) * 100)

            if len(record) != standard_size:
                records_ignored += 1
                continue

            last_updated = datetime.datetime.strptime(record[2], '%B %d, %Y').date()

            if last_updated < start_date:
                logger.info('Trial {}: Trial date {} is less than start date {}.'.format(i, last_updated, start_date))
            else:
                yield (
                    record[5],
                    {'record': record}
                )
                records_harvested += 1
        logging.info('Total records harvested %d for date range %s - %s', records_harvested, start_date, end_date)
        logging.info('Total records ignored %d for incorrect csv formatting', records_ignored)
