import logging

from bs4 import BeautifulSoup
from furl import furl
import pendulum

from share.harvest.harvester import Harvester

logger = logging.getLogger('__name__')


class SSRNHarvester(Harvester):
    base_url = furl('https://papers.ssrn.com/sol3/JELJOUR_Results.cfm')
    codes = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum):
        return self.fetch_records(start_date, end_date)

    # For each code, go through each page and call fetch_page_results on that page, then call fetch_work on each work
    def fetch_records(self, start_date, end_date):
        logger.info('Harvesting % - %s', start_date, end_date)
        self.base_url.args['stype'] = 'desc'
        self.base_url.args['SortOrder'] = 'ab_approval_date'
        for code in self.codes:
            logger.info('Results with JEL code %s', code)
            page_number = 0
            self.base_url.args['code'] = code
            while True:
                page_number += 1
                self.base_url.args['npage'] = page_number
                urls, final_page = self.fetch_page_results(self.base_url, start_date, end_date)
                for url in urls:
                    work = self.fetch_work('https://papers.ssrn.com/sol3/' + url)
                    work['code'] = code
                    work['url'] = url.replace('papers.cfm?abstract_id=', '')
                    work['id'] = url.replace('https://papers.ssrn.com/papers.cfm?abstract_id=', '')
                    yield work['id'], work
                if final_page:
                    break

    # Fetch the list of work urls on a single result page and return results within date range
    def fetch_page_results(self, url, start_date, end_date):
        logger.debug('Fetching page %s', url)
        r = self.requests.get(url.url)
        r.raise_for_status()
        results = BeautifulSoup(r.text, 'html.parser').select('font > strong > a')[1:]
        return self.check_result_dates(results, start_date, end_date)

    # Find the works which are within the specified date range
    def check_result_dates(self, soup, start_date, end_date):
        """
        :return: final_page
        """
        results = []
        for url in soup:
            # This is the element after the one that says 'Date posted: '
            date_string = url.parent.parent.parent.select('font > i')[0].next_sibling
            date_object = pendulum.strptime(date_string, '%B %d, %Y')
            if date_object < start_date:
                return results, True
            if date_object > end_date:
                continue
            results.append(url.get('href'))
        if not results:
            return [], True
        return results, False

    def fetch_work(self, url):
        r = self.requests.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')
        data = {tag['name']: tag['content'] for tag in soup.find_all('meta')[1:]}
        data['citation_author'] = [tag['content'] for tag in soup.find_all('meta', {'name': 'citation_author'})]
        return data
