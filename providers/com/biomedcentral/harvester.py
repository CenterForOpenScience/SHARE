from datetime import timedelta

from furl import furl

from django.conf import settings

from share import Harvester


class BiomedCentralHarvester(Harvester):

    def __init__(self, app_config):
        super().__init__(app_config)
        self.offset = 1
        self.page_size = 100
        self.url = 'https://api.springer.com/meta/v1/json'

    def do_harvest(self, start_date, end_date):
        if not settings.SPRINGER_API_KEY:
            raise Exception('SPRINGER_API_KEY not provided')

        end_date = end_date.date()
        start_date = start_date.date()

        # BioMed Central API only accepts a specific date, not a date range, for retrieving articles
        # so we must create our own list of dates
        dates = [start_date + timedelta(n) for n in range((end_date - start_date).days + 1)]

        for date in dates:
            yield from self.fetch_records(date)

    def fetch_records(self, date):
        self.offset = 0
        resp = self.requests.get(self.build_url(date))
        total = int(resp.json()['result'][0]['total'])

        while self.offset < total:
            records = resp.json()['records']

            for record in records:
                yield (record['identifier'], record)

            self.offset += len(records)
            resp = self.requests.get(self.build_url(date))

    def build_url(self, date):
        return furl(self.url).set(query_params={
            'api_key': settings.SPRINGER_API_KEY,
            'q': 'date:{}'.format(date),
            'p': self.page_size,
            's': self.offset
        }).url
