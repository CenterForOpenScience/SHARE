import logging
import re

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
        count, page = 0, 0
        resp = self.requests.get(furl(url).set(query_params={'page': page}))
        total = int(BeautifulSoup(resp.content, 'html.parser').find(id='page-title').text.split(' ')[0].strip())

        logging.info('Found %d results from biorxiv', total)

        while count < total:
            links = re.findall(b'href="(/content/early/[^"]+?/[^"]+)"', resp.content)

            for link in links:
                article = self.requests.get('http://biorxiv.org' + link.decode())
                soup = BeautifulSoup(article.content, 'lxml')

                data = {
                    'subject-areas': [
                        subject.a.text.strip()
                        for subject in
                        soup.find_all(**{'class': 'highwire-article-collection-term'})
                    ]
                }

                for meta in BeautifulSoup(article.content, 'lxml').find_all('meta'):
                    if 'name' not in meta.attrs:
                        continue
                    if meta.attrs['name'] in data:
                        if not isinstance(data[meta.attrs['name']], list):
                            data[meta.attrs['name']] = [data[meta.attrs['name']]]
                        data[meta.attrs['name']].append(meta.attrs['content'])
                    else:
                        data[meta.attrs['name']] = meta.attrs['content']

                count += 1
                yield link.decode(), data

            page += 1
            resp = self.requests.get(furl(url).set(query_params={'page': page}))
