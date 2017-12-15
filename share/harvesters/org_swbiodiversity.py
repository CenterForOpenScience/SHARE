import itertools
import logging
import re

from bs4 import BeautifulSoup, Comment
from furl import furl

from share.harvest import BaseHarvester


logger = logging.getLogger(__name__)


class SWHarvester(BaseHarvester):
    """

    """
    VERSION = 1

    def _do_fetch(self, start, end, list_url):
        end_date = end.date()
        start_date = start.date()
        logger.info('Harvesting swbiodiversity %s - %s', start_date, end_date)
        return self.fetch_records(list_url)

    def fetch_records(self, list_url):
        response = self.requests.get(list_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        records = soup.find_all('a')

        record_list = []
        for record in records:
            record_content = re.findall('collid=(\d+)', record.get('href'))
            if record_content and record_content[0] not in record_list:
                record_list.append(record_content[0])
        total = len(record_list)

        logging.info('Found %d results from swbiodiversity', total)

        for count, identifier in enumerate(record_list):

            logger.info('On collection %d of %d (%d%%)', count, total, (count / total) * 100)

            collection_page = furl(list_url)
            collection_page.args['collid'] = identifier
            response = self.requests.get(collection_page.url)
            response.raise_for_status()

            raw_data = BeautifulSoup(response.content, 'html.parser')
            # Peel out script tags and css things to minimize size of HTML
            for el in itertools.chain(
                    raw_data('img'),
                    raw_data('link', rel=('stylesheet', 'dns-prefetch')),
                    raw_data('link', {'type': re.compile('.')}),
                    raw_data('noscript'),
                    raw_data('script'),
                    raw_data(string=lambda x: isinstance(x, Comment)),
            ):
                el.extract()

            record = raw_data.find(id='innertext')

            yield collection_page.url, str(record)
