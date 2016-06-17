from datetime import timedelta

from celery.schedules import crontab

from share.core import Harvester


class FigshareHarvester(Harvester):

    url = 'https://api.figshare.com/v1/articles/search?search_for=*&from_date={}&to_date={}'
    schedule = crontab(minute=0, hour=0)

    def shift_range(self, start_date, end_date):
        """ Figshare should always have a 24 hour delay because they
        manually go through and check for test projects. Most of them
        are removed within 24 hours.
        So, we will shift everything back a day with harvesting to ensure
        nothing is harvested on the day of.
        """
        return (start_date - timedelta(days=1)), (end_date - timedelta(days=1))

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()

        return self.fetch_records(self.url.format(start_date.isoformat(), end_date.isoformat()))

    def fetch_records(self, url):
        page = 1
        resp = self.requests.get(url)
        total = resp.json()['items_found']
        records = [(item['article_id'], self.encode_json(item)) for item in resp.json()['items']]

        while len(records) < total:
            page += 1
            resp = self.requests.get(url + '&page={}'.format(page))
            records.extend((item['article_id'], self.encode_json(item)) for item in resp.json()['items'])

        return records
