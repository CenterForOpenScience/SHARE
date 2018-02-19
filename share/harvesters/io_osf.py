import logging
import datetime

from django.conf import settings

from furl import furl

from share.harvest import BaseHarvester


QA_TAG = 'qatest'
logger = logging.getLogger(__name__)


class OSFHarvester(BaseHarvester):
    VERSION = 1

    def build_url(self, start_date, end_date, path, query_params):
        # so prod SHARE doesn't get throttled
        if settings.OSF_BYPASS_THROTTLE_TOKEN:
            self.session.headers.update({'X-THROTTLE-TOKEN': settings.OSF_BYPASS_THROTTLE_TOKEN})

        url = furl(settings.OSF_API_URL + path)
        url.args['page[size]'] = 100
        # url.args['filter[public]'] = 'true'
        # OSF turns dates into date @ midnight so we have to go ahead one more day
        url.args['filter[date_modified][gte]'] = start_date.date().isoformat()
        url.args['filter[date_modified][lte]'] = (end_date + datetime.timedelta(days=2)).date().isoformat()
        for param, value in (query_params or {}).items():
            url.args[param] = value
        return url

    def do_harvest(self, start_date, end_date, path, query_params=None, embed_attrs=None):
        return self.fetch_records(self.build_url(start_date, end_date, path, query_params), embed_attrs)

    def fetch_records(self, url, embed_attrs):
        while True:
            records, next_page = self.fetch_page(url)

            for record in records.json()['data']:
                if record['attributes'].get('tags') and QA_TAG in record['attributes']['tags']:
                    continue

                record = self.populate_embeds(record, embed_attrs)

                yield record['id'], record

            if not next_page:
                break

    def fetch_page(self, url, next_page=None):
        logger.debug('Making request to {}'.format(url.url))

        records = self.requests.get(url.url)

        if records.status_code // 100 != 2:
            raise ValueError('Malformed response ({}) from {}. Got {}'.format(records, url.url, records.content))

        next_page = records.json()['links'].get('next')
        next_page = furl(next_page) if next_page else None

        logger.debug('Found {} records.'.format(len(records.json()['data'])))

        return records, next_page

    def populate_embeds(self, record, embed_attrs):
        for attr, key in (embed_attrs or {}).items():
            embedded = record
            try:
                for key in key.split('.'):
                    embedded = embedded[key]
            except KeyError:
                logger.warning('Could not access attribute %s at %s', attr, key)
                continue

            logger.info('Populating embedded attribute "{}" for "{}"'.format(attr, record['id']))

            data = []
            url = furl(embedded).add(args={'page[size]': 100})

            while True:
                resp, url = self.fetch_page(url)
                data.extend(resp.json()['data'])

                if not url:
                    break

            record[attr] = data
        return record
