import logging
import re

import arrow
from furl import furl
from bs4 import BeautifulSoup

from share import Harvester

logger = logging.getLogger(__name__)


class BiorxivHarvester(Harvester):
    url = 'http://biorxiv.org/search/'

    def do_harvest(self, start_date, end_date):

        end_date = end_date.date()
        start_date = start_date.date()

        # I wish I was wrong, the url is just "<key1>:<value> <key2>:<value>" and so on
        url = furl(self.url).add(
            path=' '.join([
                'limit_from:{}'.format(start_date),
                'limit_to:{}'.format(end_date),
                'numresults:100',
                'sort:publication-date',
                'direction:descending',
                'format_result:standard',
            ])
        ).url

        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(url, start_date, end_date)

    def fetch_records(self, url, start_date, end_date):
        page = -1

        while True:
            page += 1
            resp = self.requests.get(furl(url).set(query_params={'page': page}))
            links = re.findall(b'href="(/content/early/[^"]+?/[^"]+)"', resp.content)

            if not links:
                return

            for link in links:
                date = arrow.get('-'.join(link.decode().split('/')[3:-1])).date()
                if date < start_date or date > end_date:  # Biorxiv's search sometimes "leaks"
                    return

                article = self.requests.get('http://biorxiv.org' + link.decode())

                yield (link.decode(), {
                    meta.attrs['name']: meta.attrs['content']
                    for meta in BeautifulSoup(article.content, 'html.parser').find_all('meta')
                    if 'name' in meta.attrs
                })
