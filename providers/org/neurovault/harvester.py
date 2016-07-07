from share.harvest.harvester import Harvester


class NeuroVaultHarvester(Harvester):
    url = 'http://www.neurovault.org/api/collections/?format=json'

    def do_harvest(self, start_date, end_date):
        api_url = self.url
        while api_url:
            response = self.requests.get(api_url)
            records = response.json()
            for record in records['results']:
                record_id = record['id']
                yield(record_id, record)

            api_url = records['next']
