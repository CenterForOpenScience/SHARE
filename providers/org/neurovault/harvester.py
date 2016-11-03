import pendulum

from share.harvest.harvester import Harvester


class NeuroVaultHarvester(Harvester):
    url = 'http://www.neurovault.org/api/collections/?format=json'

    def do_harvest(self, start_date, end_date):
        api_url = self.url
        while api_url:
            response = self.requests.get(api_url)
            records = response.json()
            for record in records['results']:
                date = pendulum.parse(record['modify_date'])
                if date < start_date:
                    return  # We're all caught up
                if date > end_date:
                    continue  # Reaching too far back

                yield record['id'], record

            api_url = records['next']
