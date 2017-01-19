from furl import furl

from share.harvest.harvester import Harvester

# Built by inspecting http://www.researchregistry.com/browse-the-registry.html
class ResearchRegistryHarvester(Harvester):
    API_URL = 'https://us-api.knack.com/v1/scenes/scene_3/views/view_4/records'
    HEADERS = {
        'X-Knack-Application-Id': '54a1ac1032e4beb07e04ac2c',
        'X-Knack-REST-API-Key': 'renderer'
    }
    DATE_FIELD = 'field_2'  # Registration Date
    ID_FIELD = 'field_21'  # Research Registry UIN

    def fetch_page(self, page, start_date, end_date):
        url = furl(self.API_URL)
        url.args['page'] = page
        url.args['rows_per_page'] = 1000
        url.args['format'] = 'raw'
        url.args['filter'] = {
            'match': 'and',
            'rules': [
                {'field': self.DATE_FIELD, 'operator': 'is after', 'value': start_date},
                {'field': self.DATE_FIELD, 'operator': 'is before', 'value': end_date},
            ]
        }
        response = self.requests.get(url.url, headers=self.HEADERS)
        if response.status_code // 100 != 2:
            raise ValueError('Malformed response ({}) from {}. Got {}'.format(response, url.url, response.content))
        return response.json()


    def do_harvest(self, start_date, end_date):
        page = 1
        while True:
            data = self.fetch_page(page, start_date, end_date)
            total_pages = data['total_pages']
            records = data['records']
            for r in records:
                yield r[self.ID_FIELD], r
            if page >= total_pages:
                break
            page += 1
