import arrow
from furl import furl

from bs4 import BeautifulSoup

import logging
from share import Harvester

logger = logging.getLogger(__name__)


class PhilicaHarvester(Harvester):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = 'http://philica.com/display_article.php'
        self.main_url = 'http://philica.com/index.php'

    def do_harvest(self, start_date: arrow.Arrow, end_date: arrow.Arrow):

        return self.fetch_records(self.base_url, start_date, end_date)

    def fetch_records(self, url, start_date, end_date):

        logger.info('Making request to {}'.format(url))

        yield from self.fetch_page(url, start_date, end_date)

        logger.info("Philica has been harvested")

    def fetch_page(self, url, start_date, end_date, preprint=''):
        main_page = self.requests.get(self.main_url)
        moup = BeautifulSoup(main_page.content, 'html.parser')

        table = moup.find('td').find('p', 'standard')
        table_links = table.find_all(lambda tag: tag.name == u'a')

        latest_article = [table_li.attrs for table_li in table_links]
        latest_article = latest_article[0]['href'].split('=')[1]  # grabs the most recent article number
        # Grabbing information for the head of the article as
        # Philica has no API, so we have to search iteratively
        for x in range(int(latest_article), 1, -1):
            attr_list = []
            url = furl(url).set(query_params={'article_id': x})
            records = self.requests.get(url)

            soup = BeautifulSoup(records.content, 'html.parser')
            article_list = soup.head.find_all(lambda tag: tag.name == 'meta' or tag.name == 'link')

            for tag in article_list:
                if 'name' in tag.attrs and tag.attrs['name'] == 'DC.date':
                    if arrow.get(tag.attrs['content'], 'YYYY-MM-DD HH:mm:ss') < start_date:
                        return

                    if arrow.get(tag.attrs['content'], 'YYYY-MM-DD HH:mm:ss') > end_date:
                        continue

                attr_list.append(tag.attrs)

            # Check if the article is missing, some are randomly throughout
            if soup.html.head.title.text == 'Philica Article':
                continue

            yield (x, {'data': attr_list})
