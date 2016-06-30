from datetime import timedelta
from furl import furl

from share import Harvester
from django.conf import settings


class BiomedCentralHarvester(Harvester):
    url = 'http://api.springer.com/meta/v1/json'

    def do_harvest(self, start_date, end_date):

        if not settings.BIOMEDCENTRAL_API_KEY:
            raise Exception('BioMed Central api key not provided')

        start_date = start_date.date()
        end_date = end_date.date()

        # API only accepts a specific date, not a date range, for retrieving articles
        # so we must create our own list of dates
        dates = [start_date + timedelta(n) for n in range((end_date - start_date).days + 1)]

        for date in dates:
            return self.fetch_records(furl(self.url).set(query_params={
                'api_key': settings.BIOMEDCENTRAL_API_KEY,
                'q': 'date:{}'.format(date),
            }).url)

    def fetch_records(self, url):
        resp = self.requests.get(url)
        total = int(resp.json()['result'][0]['total'])
        total_processed = 0

        while total_processed < total:
            response = self.requests.get(furl(url).add(query_params={
                'p': 100,
                's': total_processed
            }).url)

            records = response.json()['records']
            for record in records:
                print(record['identifier'])
                print(record)
                yield (record['identifier'], record)

            total_processed += 100

