import pendulum

import logging
from share.harvest import BaseHarvester

logger = logging.getLogger(__name__)


class PeerJHarvester(BaseHarvester):
    VERSION = 1

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum, identifier_prefix='', fetch_xml=False):
        url = self.config.base_url
        while True:
            logger.debug('Fetching page %s', url)
            resp = self.requests.get(url)
            resp.raise_for_status()
            resp_data = resp.json()

            for record in resp_data['_items']:
                if pendulum.parse(record['date']) < start_date:
                    logger.info('%s is before %s, ending harvest', record['date'], start_date)
                    return

                if pendulum.parse(record['date']) > end_date:
                    logger.debug('%s is after %s, skipping', record['date'], end_date)
                    continue

                doc_id = identifier_prefix + record['identifiers']['peerj']

                if fetch_xml:
                    logger.debug('Fetching article %s', record['_links']['alternate']['xml']['href'])
                    details = self.requests.get(record['_links']['alternate']['xml']['href'])
                    details.raise_for_status()
                    yield doc_id, details.content
                else:
                    yield doc_id, record

            if 'next' not in resp_data['_links']:
                logger.info('No "next" key found, ending harvest')
                return
            url = resp_data['_links']['next']['href']
