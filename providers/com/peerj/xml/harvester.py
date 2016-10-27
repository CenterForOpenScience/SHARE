import pendulum

import logging
from share import Harvester

logger = logging.getLogger('com.peerj')


class PeerJXMLHarvester(Harvester):
    base_url = 'https://peerj.com/articles/index.json'

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum):
        url = self.base_url
        while True:
            logger.debug('Fetching page %s', url)
            resp = self.requests.get(url)

            for record in resp.json()['_items']:
                if pendulum.parse(record['date']) < start_date:
                    return

                if pendulum.parse(record['date']) > end_date:
                    continue

                logger.debug('Fetching article %s', record['_links']['alternate']['xml']['href'])
                details = self.requests.get(record['_links']['alternate']['xml']['href'])
                details.raise_for_status()

                yield record['@id'], details.content

            if 'next' not in record['_links']:
                return
            url = record['_links']['next']['href']
