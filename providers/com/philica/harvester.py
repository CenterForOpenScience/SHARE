import arrow
from furl import furl
from datetime import timedelta

from bs4 import BeautifulSoup

import logging
from share import Harvester

logger = logging.getLogger(__name__)


class PhilicaHarvester(Harvester):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = 'http://philica.com/display_article.php'

    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow):

        return self.fetch_records(self.base_url, (start_date - timedelta(days=1)), (end_date - timedelta(days=1)))

    def fetch_records(self, url, start_date, end_date):

        logger.info('Making request to {}'.format(url))

        yield from self.fetch_page(url, start_date, end_date)

        logger.info("Philica has been harvested")

    def fetch_page(self, url, start_date, end_date, preprint=''):
        # Grabbing information for the head of the article as
        # Philica has no API, so we have to search iteratively
        for x in range(1, 662):
            url = furl(url).set(query_params={'article_id': x})
            records = self.requests.get(url)
            soup = BeautifulSoup(records.content, 'html.parser')
            article_list = soup.head.find_all(lambda tag: tag.name == u'meta' or tag.name == u'link')
            attr_list = [tag.attrs for tag in article_list]
            # Check for if the article is missing, some are randomly throughout
            if soup.html.head.title.text == 'Philica Article':
                continue

            yield (x, {'data': attr_list})
