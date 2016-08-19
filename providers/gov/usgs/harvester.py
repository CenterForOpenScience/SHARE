from furl import furl

from datetime import date

from share.harvest.harvester import Harvester


class USGSHarvester(Harvester):
    url = 'https://pubs.er.usgs.gov/pubs-services/publication'

    def do_harvest(self, start_date, end_date):
        today = date.today()
        end_date = end_date.date()
        start_date = start_date.date()

        end_days_back = (today - end_date).days
        start_days_back = (today - start_date).days

        # The USGS API does not support date ranges
        for days_back in range(end_days_back, start_days_back):
            page = 1
            page_size = 100

            while True:
                resp = self.requests.get(furl(self.url).set(query_params={
                    'mod_x_days': days_back + 1,
                    'page_number': page,
                    'page_size': page_size
                }).url)

                records = resp.json()['records']

                for record in records:
                    record_id = record['id']
                    yield (record_id, record)

                if len(records) < page_size:
                    break

                page += 1
