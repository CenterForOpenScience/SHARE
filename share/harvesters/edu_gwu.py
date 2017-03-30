import logging
import pendulum

from furl import furl
from bs4 import BeautifulSoup

from share.harvest import BaseHarvester

logger = logging.getLogger(__name__)


class GWScholarSpaceHarvester(BaseHarvester):
    VERSION = 1

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()

        # There is no apparent way to filter by date range, just sort by date.
        url = furl(self.config.base_url + '/catalog')
        url.args['per_page'] = 10  # If it gets more active, consider upping to 50 or 100
        url.args['sort'] = 'system_modified_dtsi+desc'

        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(url, start_date, end_date)

    def fetch_records(self, url, start_date, end_date):
        count, page = 0, 1
        resp = self.requests.get(furl(url).set(query_params={'page': page}))
        soup = BeautifulSoup(resp.content, 'lxml')
        try:
            total = int(soup.select('#sortAndPerPage .page_entries strong')[-1].text.replace(',', ''))
        except IndexError:
            total = 0

        logging.info('Found %d results from GW ScholarSpace', total)

        while count < total:
            links = map(lambda a: a['href'], soup.select('#search-results li h2 > a'))

            if not links:
                break

            logger.info('On document %d of %d (%d%%)', count, total, (count / total) * 100)
            for link in links:
                item_response = self.requests.get(self.config.base_url + link)
                if item_response.status_code // 100 != 2:
                    logger.warning('Got non-200 status %s from %s', item_response, link)
                    continue
                item_response.raise_for_status()
                soup = BeautifulSoup(item_response.content, 'lxml')

                # Skip records outside the date range
                date_modified = pendulum.parse(soup.find(itemprop='dateModified').text)
                if date_modified > end_date:
                    continue
                if date_modified < start_date:
                    return

                item = soup.find(id='content').find(itemscope=True)

                count += 1
                yield link, str(item)

            page += 1
            resp = self.requests.get(furl(url).set(query_params={'page': page}))
            soup = BeautifulSoup(resp.content, 'lxml')
