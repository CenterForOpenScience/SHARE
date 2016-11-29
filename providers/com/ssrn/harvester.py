import logging

from bs4 import BeautifulSoup
from furl import furl
import lxml
import pendulum

from share.harvest.harvester import Harvester

logger = logging.getLogger('__name__')


class SSRNHarvester(Harvester):
    base_url = furl('https://papers.ssrn.com/sol3/JELJOUR_Results.cfm')
    codes = ['A0', 'A1', 'A2', 'A3', 'B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'C0', 'C01', 'C02', 'C1', 'C2', 'C3', 'C4',
             'C5', 'C6', 'C7', 'C8', 'C9', 'D0', 'D01', 'D02', 'D03', 'D04', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7',
             'D8', 'D9', 'E0', 'E01', 'E02', 'E03', 'E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'F0', 'F01', 'F02', 'F1', 'F2',
             'F3', 'F4', 'F5', 'F6', 'G0', 'G01', 'G02', 'G1', 'G2', 'G3', 'H0', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
             'H7', 'H8', 'I0', 'I1', 'I2', 'I3', 'J0', 'J01', 'J08', 'J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8',
             'K0', 'K1', 'K2', 'K3', 'K4', 'L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9', 'M0', 'M1', 'M2',
             'M3', 'M4', 'M5', 'N0', 'N01', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9', 'O0', 'O1', 'O2',
             'O3', 'O4', 'O5', 'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'Q0', 'Q01', 'Q02', 'Q1', 'Q2', 'Q3', 'Q4', 'Q5',
             'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'Y0', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y6', 'Y7', 'Y8', 'Y9', 'Z0', 'Z1',
             'Z2', 'Z3']

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum):
        return self.fetch_records(start_date, end_date)

    # For each code, go through each page and call fetch_page_results on that page, then call fetch_work on each work
    def fetch_records(self, start_date, end_date):
        self.base_url.args['stype'] = 'desc'
        self.base_url.args['SortOrder'] = 'ab_approval_date'
        for code in self.codes:
            logger.info('Results with JEL code {}'.format(code))
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
        r = self.requests.get(url.url)
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
        soup = BeautifulSoup(r.text, 'lxml')
        data = {tag['name']: tag['content'] for tag in soup.find_all('meta')[1:]}
        data['citation_author'] = [tag['content'] for tag in soup.find_all('meta', {'name': 'citation_author'})]
        return data
