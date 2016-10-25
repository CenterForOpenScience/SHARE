import pendulum

from furl import furl

from share import Harvester


class FigshareHarvester(Harvester):
    page_size = 50
    url = 'https://api.figshare.com/v2/articles'

    def do_harvest(self, start_date, end_date):

        return self.fetch_records(furl(self.url).set(query_params={
            'order_direction': 'asc',
            'order': 'modified_date',
            'page_size': self.page_size,
            'modified_date': start_date.date().isoformat(),
        }).url, end_date.date())

    def fetch_records(self, url, end_day):
        page, detail = 0, None

        while True:
            page += 1
            resp = self.requests.get(furl(url).add(query_params={
                'page': page,
            }).url)

            if resp.status_code == 422:
                # We've asked for too much. Time to readjust date range
                # Thanks for leaking variables python
                page, url = 0, furl(url).add(query_params={
                    'modified_date': pendulum.parse(detail['modified_date']).date().isoformat()
                })
                continue

            for item in resp.json():
                resp = self.requests.get(item['url'])
                detail = resp.json()

                if pendulum.parse(detail['modified_date']).date() > end_day:
                    return

                yield item['url'], detail

            if len(resp.json()) < self.page_size:
                return  # We've hit the end of our results
