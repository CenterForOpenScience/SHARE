from datetime import timedelta

from furl import furl

from django.conf import settings

from share import Harvester


class BiomedCentralHarvester(Harvester):
    url = 'http://api.springer.com/meta/v1/json'
    page_size = 100
    offset = 1

    def do_harvest(self, start_date, end_date):
        if not settings.BIOMEDCENTRAL_API_KEY:
            raise Exception('BioMed Central api key not provided')

        start_date = start_date.date()
        end_date = end_date.date()

        # API only accepts a specific date, not a date range, for retrieving articles
        # so we must create our own list of dates
        dates = [start_date + timedelta(n) for n in range((end_date - start_date).days + 1)]

        for date in dates:
            yield from self.fetch_records(date)

    def fetch_records(self, date):
        self.offset = 1
        resp = self.requests.get(self.build_url(date))
        total = int(resp.json()['result'][0]['total'])
        total_processed = 0

        while total_processed < total:
            records = resp.json()['records']

            for record in records:
                yield (record['identifier'], record)

            total_processed += len(records)
            self.offset += len(records)
            resp = self.requests.get(self.build_url(date))

    def build_url(self, date):
        return furl(self.url).set(query_params={
            'api_key': settings.BIOMEDCENTRAL_API_KEY,
            'q': 'date:{}'.format(date),
            'p': self.page_size,
            's': self.offset
        }).url
