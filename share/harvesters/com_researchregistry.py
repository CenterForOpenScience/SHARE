import json
from furl import furl

from django.conf import settings

from share.harvest import BaseHarvester


# Built by inspecting http://www.researchregistry.com/browse-the-registry.html
class ResearchRegistryHarvester(BaseHarvester):
    VERSION = '0.0.1'

    HEADERS = {
        'X-Knack-Application-Id': settings.RESEARCHREGISTRY_APPLICATION_ID,
        'X-Knack-REST-API-Key': settings.RESEARCHREGISTRY_API_KEY
    }
    DATE_FIELD = 'field_2'  # Registration Date
    ID_FIELD = 'field_21'  # Research Registry UIN

    def fetch_page(self, page, start_date, end_date):
        url = furl(self.config.base_url)
        url.args['page'] = page
        url.args['rows_per_page'] = 1000
        url.args['format'] = 'raw'
        url.args['filters'] = json.dumps({
            'match': 'and',
            'rules': [
                # date filters are strictly less/greater than, not equal to
                {'field': self.DATE_FIELD, 'operator': 'is after', 'value': start_date.subtract(days=1).to_date_string()},
                {'field': self.DATE_FIELD, 'operator': 'is before', 'value': end_date.add(days=1).to_date_string()},
            ]
        })
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
