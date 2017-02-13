from furl import furl

from share import Harvester


class CrossRefHarvester(Harvester):
    url = 'https://api.crossref.org/v1/works'

    def do_harvest(self, start_date, end_date):
        start_date = start_date.date()
        end_date = end_date.date()

        return self.fetch_records(furl(self.url).set(query_params={
            'filter': 'from-update-date:{},until-update-date:{}'.format(
                start_date.isoformat(),
                end_date.isoformat()
            ),
            'rows': 1000,
        }))

    def fetch_records(self, url: furl):
        cursor = '*'

        while True:
            url.args['cursor'] = cursor
            resp = self.requests.get(url.url)
            resp.raise_for_status()
            message = resp.json()['message']
            records = message['items']
            cursor = message['next-cursor']

            if not records:
                break
            for record in records:
                yield (record['DOI'], record)
