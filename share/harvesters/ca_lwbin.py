import pendulum

from furl import furl

from share.harvest.base import BaseHarvester


class LWBINHarvester(BaseHarvester):
    VERSION = 1

    # LWBIN does not have an HTTPS URL
    limit = 100

    def do_harvest(self, start_date, end_date):
        page = 0

        while True:
            # Searching by time is not permitted by the LWBIN CKAN API. All records must be scanned each time.
            page += 1
            response = self.requests.get(furl(self.config.base_url).set(query_params={
                'limit': self.limit,
                'page': page,
            }).url)

            for record in response.json()['result']:
                date = pendulum.parse(record['metadata_modified'])
                if date < start_date:
                    return  # We're all caught up
                if date > end_date:
                    continue  # Reaching too far back

                yield record['id'], record

            if len(response.json()['result']) != self.limit:
                break
