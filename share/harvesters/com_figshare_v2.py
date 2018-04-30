import pendulum

from furl import furl

from share.harvest import BaseHarvester


class FigshareHarvester(BaseHarvester):
    VERSION = 1

    page_size = 50

    def _do_fetch(self, start_date, end_date):
        url = furl(self.config.base_url).set(query_params={
            'order_direction': 'asc',
            'order': 'modified_date',
            'page_size': self.page_size,
            'modified_since': start_date.date().isoformat(),
        })
        return self.fetch_records(url, end_date.date())

    def fetch_records(self, url, end_day):
        page = 1
        last_seen_day = None

        while True:
            page += 1
            url.args['page'] = page
            resp = self.requests.get(url.url)

            if last_seen_day and resp.status_code == 422:
                # We've asked for too much. Time to readjust date range
                url.args['modified_since'] = last_seen_day.isoformat()
                page = 0
                continue

            for item in resp.json():
                resp = self.requests.get(item['url'])
                detail = resp.json()
                last_seen_day = pendulum.parse(detail['modified_date']).date()

                if last_seen_day > end_day:
                    return

                yield item['url'], detail

            if len(resp.json()) < self.page_size:
                return  # We've hit the end of our results
