from furl import furl

from share.harvest.harvester import Harvester


class USGSHarvester(Harvester):
    url = 'https://pubs.er.usgs.gov/pubs-services/publication'

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()

        days_back = (end_date - start_date).days

        resp = self.requests.get(furl(self.url).set(query_params={
            'mod_x_days': days_back,
        }).url)

        records = resp.json()['records']
        page = 1

        while records:
            for record in records:
                record_id = record['id']
                yield(record_id, record)

            page += 1
            resp = self.requests.get(furl(self.url).set(query_params={
                'mod_x_days': days_back,
                'page_number': page,
            }).url)

            records = resp.json()['records']
