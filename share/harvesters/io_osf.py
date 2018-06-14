import logging
import datetime

from django.conf import settings

from furl import furl

from share.exceptions import HarvestError
from share.harvest import BaseHarvester


QA_TAG = 'qatest'
logger = logging.getLogger(__name__)


class NodeSuddenlyUnavailable(HarvestError):
    # A node was deleted or made private after it was seen at /v2/nodes,
    # but before we could fetch its embeds
    pass


class OSFHarvester(BaseHarvester):
    VERSION = 1

    # override BaseHarvester._do_fetch
    def _do_fetch(self, start_date, end_date, path, query_params=None, embed_attrs=None):
        return self._fetch_records(self._build_url(start_date, end_date, path, query_params), embed_attrs)

    # override BaseHarvester._do_fetch_by_id
    def _do_fetch_by_id(self, guid, path, query_params=None, embed_attrs=None):
        url = self._build_guid_url(guid, path, query_params).url
        response = self.requests.get(url)

        if response.status_code // 100 != 2:
            raise ValueError('Malformed response ({}) from {}. Got {}'.format(response, url, response.content))

        logger.debug('Fetched record "%s"', guid)

        record = response.json()['data']
        return self._populate_embeds(record, embed_attrs)

    def _setup_session(self):
        # so prod SHARE doesn't get throttled
        if settings.OSF_BYPASS_THROTTLE_TOKEN:
            self.session.headers.update({'X-THROTTLE-TOKEN': settings.OSF_BYPASS_THROTTLE_TOKEN})

    def _build_url(self, start_date, end_date, path, query_params):
        self._setup_session()

        url = furl(settings.OSF_API_URL + path)
        url.args['page[size]'] = 100
        # url.args['filter[public]'] = 'true'
        # OSF turns dates into date @ midnight so we have to go ahead one more day
        url.args['filter[date_modified][gte]'] = start_date.date().isoformat()
        url.args['filter[date_modified][lte]'] = (end_date + datetime.timedelta(days=2)).date().isoformat()
        for param, value in (query_params or {}).items():
            url.args[param] = value
        return url

    def _build_guid_url(self, guid, path, query_params):
        self._setup_session()

        url = furl(settings.OSF_API_URL)
        url.path.add(path).add(guid)
        for param, value in (query_params or {}).items():
            url.args[param] = value
        return url

    def _fetch_records(self, url, embed_attrs):
        while True:
            records, next_page = self._fetch_page(url)

            for record in records.json()['data']:
                if record['attributes'].get('tags') and QA_TAG in record['attributes']['tags']:
                    continue

                try:
                    record = self._populate_embeds(record, embed_attrs)
                except NodeSuddenlyUnavailable:
                    continue

                yield record['id'], record

            if not next_page:
                break

    def _fetch_page(self, url, next_page=None):
        logger.debug('Making request to {}'.format(url.url))

        records = self.requests.get(url.url)

        if records.status_code in (401, 410):
            raise NodeSuddenlyUnavailable('Node unharvestable ({}) at {}. Got {}'.format(records. url.url, records.content))
        if records.status_code // 100 != 2:
            raise ValueError('Malformed response ({}) from {}. Got {}'.format(records, url.url, records.content))

        next_page = records.json()['links'].get('next')
        next_page = furl(next_page) if next_page else None

        logger.debug('Found {} records.'.format(len(records.json()['data'])))

        return records, next_page

    def _populate_embeds(self, record, embed_attrs):
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
                resp, url = self._fetch_page(url)
                data.extend(resp.json()['data'])

                if not url:
                    break

            record[attr] = data
        return record
