from furl import furl

from django.conf import settings

from share import Harvester


class MendeleyHarvester(Harvester):
    url = 'https://api.mendeley.com/v1/datasets?fields=results.*&limit=500'

    def do_harvest(self, start_date, end_date):
        if not settings.MENDELEY_API_CLIENT_ID or not settings.MENDELEY_API_CLIENT_SECRET:
            raise Exception('Mendeley authorization information not provided')

        # Inputs are a DateTime object, many APIs only accept dates
        end_date = end_date.date()
        start_date = start_date.date()

        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(furl(self.url).set(query_params={
            # 'to_date': end_date.isoformat(),
            'modified_since': start_date.isoformat(),
        }).url)

    def fetch_records(self, url):
        count, page = 0, 1

        resp = self.requests.get(url)
        total = resp.json()['items_found']

        while True:
            if count >= total:
                break

            for item in resp.json()['items']:
                count += 1
                yield (item['article_id'], item)

            page += 1
            resp = self.requests.get(furl(url).add(query_params={'page': page}).url)
