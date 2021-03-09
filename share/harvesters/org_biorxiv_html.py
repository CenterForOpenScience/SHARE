import itertools
import logging
import re

from furl import furl
from bs4 import BeautifulSoup
from bs4 import Comment

from share.harvest import BaseHarvester


logger = logging.getLogger(__name__)


class BiorxivHarvester(BaseHarvester):
    VERSION = 1

    def do_harvest(self, start_date, end_date):

        end_date = end_date.date()
        start_date = start_date.date()

        # I wish I was wrong, the url is just "<key1>:<value> <key2>:<value>" and so on
        url = furl(self.config.base_url).add(
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
        count, page = 0, 0
        resp = self.requests.get(furl(url).set(query_params={'page': page}))
        total = BeautifulSoup(resp.content, 'html.parser').find(id='page-title').text.split(' ')[0].strip().replace(',', '')

        if total == 'No':
            total = 0
        else:
            total = int(total)

        logging.info('Found %d results from biorxiv', total)

        while count < total:
            links = re.findall(b'href="(/content/early/[^"]+?/[^"]+)"', resp.content)

            logger.info('On document %d of %d (%d%%)', count, total, (count / total) * 100)

            for link in links:
                url = 'http://biorxiv.org' + link.decode()
                logger.debug('[%d/%d] Requesting %s', count, total, url)
                article = self.requests.get(url)
                article.raise_for_status()

                soup = BeautifulSoup(article.content, 'lxml')

                # Peel out script tags and css things to minimize size of HTML
                for el in itertools.chain(
                    soup('img'),
                    soup('link', rel=('stylesheet', 'dns-prefetch')),
                    soup('link', {'type': re.compile('.')}),
                    soup('noscript'),
                    soup('script'),
                    soup(string=lambda x: isinstance(x, Comment)),
                ):
                    el.extract()

                # Links have PKs and dates in them. /content/early/YYYY/MM/DD/PK or /content/early/YYYY/MM/DD/PK.REV
                identifier = re.match(r'/content/early/\d{4}/\d{2}/\d{2}/(\d+)(?:\.\d+)?$', link.decode()).group(1)

                yield identifier, str(soup)

                count += 1
            page += 1
            resp = self.requests.get(furl(url).set(query_params={'page': page}))
