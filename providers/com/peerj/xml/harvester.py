import pendulum

import logging
from share import Harvester

logger = logging.getLogger(__name__)


class PeerJXMLHarvester(Harvester):
    base_url = 'https://peerj.com/articles/index.json'

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum):
        url = self.base_url
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

                logger.debug('Fetching article %s', record['_links']['alternate']['xml']['href'])
                details = self.requests.get(record['_links']['alternate']['xml']['href'])
                details.raise_for_status()

                yield record['@id'], details.content

            if 'next' not in resp_data['_links']:
                logger.info('No "next" key found, ending harvest')
                return
            url = resp_data['_links']['next']['href']
