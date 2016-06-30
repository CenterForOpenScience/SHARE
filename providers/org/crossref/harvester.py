from furl import furl

from share import Harvester


class CrossRefHarvester(Harvester):
    url = 'http://api.crossref.org/v1/works'

    def do_harvest(self, start_date, end_date):
        start_date = start_date.date()
        end_date = end_date.date()

        return self.fetch_records(furl(self.url).set(query_params={
            'filter': 'from-pub-date:{},until-pub-date:{}'.format(
                start_date.isoformat(),
                end_date.isoformat()
            )
        }).url)

    def fetch_records(self, url):
        resp = self.requests.get(url)
        total = resp.json()['message']['total-results']

        for i in range(0, total, 1000):
            response = self.requests.get(furl(self.url).add(query_params={
                'rows': 1000,
                'offset': i
            }).url)

            records = response.json()['message']['items']
            for record in records:
                yield (record['DOI'], record)
