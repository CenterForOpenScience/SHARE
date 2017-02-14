from django.conf import settings

from furl import furl

from share.harvest import BaseHarvester


class HarvardDataverseHarvester(BaseHarvester):
    KEY = 'edu.harvarddataverse'
    VERSION = '0.0.1'

    type = 'dataset'
    MAX_ITEMS_PER_REQUEST = 1000

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()

        return self.fetch_records(furl(self.config.base_url).set(query_params={
            'q': '*',
            'type': self.type,
            'per_page': self.MAX_ITEMS_PER_REQUEST,
            'key': settings.DATAVERSE_API_KEY,
            'sort': 'date',
            'order': 'asc',
            'fq': 'dateSort:[{}T00:00:00Z TO {}T00:00:00Z]'.format(start_date.isoformat(), end_date.isoformat())
        }).url)

    def fetch_records(self, url):
        response = self.requests.get(url)
        total_num = response.json()['data']['total_count']
        num_processed = 0

        while num_processed < total_num:
            records = response.json()['data']['items']
            num_processed += len(records)

            for record in records:
                yield (record['global_id'], record)

            response = self.requests.get(furl(url).add(query_params={
                'start': str(num_processed)
            }).url)
