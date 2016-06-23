from datetime import timedelta

from furl import furl

from share import Harvester


class FigshareHarvester(Harvester):
    url = 'https://api.figshare.com/v1/articles/search'

    # Other harvesters should not have to implement this method
    def shift_range(self, start_date, end_date):
        """Figshare should always have a 24 hour delay because they
        manually go through and check for test projects. Most of them
        are removed within 24 hours.
        So, we will shift everything back a day with harvesting to ensure
        nothing is harvested on the day of.
        """
        return (start_date - timedelta(days=1)), (end_date - timedelta(days=1))

    def do_harvest(self, start_date, end_date):
        # Inputs are a DateTime object, many APIs only accept dates
        end_date = end_date.date()
        start_date = start_date.date()

        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(furl(self.url).set(query_params={
            'search_for': '*',
            'to_date': end_date.isoformat(),
            'from_date': start_date.isoformat(),
        }).url)

    def fetch_records(self, url):
        page = 1
        resp = self.requests.get(url)
        total = resp.json()['items_found']
        records = [(item['article_id'], item) for item in resp.json()['items']]

        while len(records) < total:
            page += 1
            resp = self.requests.get(furl(url).add(query_params={page: page}).url)
            records.extend((item['article_id'], item) for item in resp.json()['items'])

        return records
