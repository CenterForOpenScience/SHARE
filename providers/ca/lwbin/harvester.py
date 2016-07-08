from share.harvest.harvester import Harvester


class LWBINHarvester(Harvester):
    # LWBIN does not have an HTTPS URL
    url = 'http://130.179.67.140/api/3/action/current_package_list_with_resources'

    def do_harvest(self, start_date, end_date):
        # Searching by time is not permitted by the LWBIN CKAN API. All records must be scanned each time.
        response = self.requests.get(self.url)
        records = response.json()['result']
        for record in records:
            record_id = record['id']
            yield(record_id, record)
