import pendulum

from share.harvest import BaseHarvester


class NeuroVaultHarvester(BaseHarvester):
    KEY = 'org.neurovault'
    VERSION = '0.0.1'

    def do_harvest(self, start_date, end_date):
        api_url = self.config.base_url
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
