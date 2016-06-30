import arrow
from furl import furl
from typing import Tuple
from typing import Union
from typing import Iterator

from share.harvest.harvester import Harvester


class OSFHarvester(Harvester):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = 'https://api.osf.io/v2/nodes/?filter[public]=true'

    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow) -> Iterator[Tuple[str, Union[str, dict, bytes]]]:
        url = furl(self.url)

        url.args['filter[date_updated][gt]'] = start_date.date().isoformat()
        url.args['filter[date_updated][lt]'] = end_date.date().isoformat()

        return self.fetch_records(url)


def fetch_records(self, url: furl) -> list:
        records = self.requests.get(url.url)

        total_records = records.json()['meta']['total']
        all_records = []
        while records['links'].get('next'):
            record_list = records.json()['data']

            for record in record_list:
                all_records.append(record)

            records = self.requests.get(records.json()['links']['next'])

        total = int(records.json()['counts']['total'])

        return all_records
