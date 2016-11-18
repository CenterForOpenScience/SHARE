import logging

import pendulum
from bs4 import BeautifulSoup
from furl import furl

from share.harvest.harvester import Harvester

logger = logging.getLogger('__name__')


class SSRNHarvester(Harvester):
    base_url = furl('https://papers.ssrn.com/sol3/JELJOUR_Results.cfm')
    # codes = ['A0', 'A1', 'A2', 'A3', 'B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'C0', 'C01', 'C02', 'C1', 'C2', 'C3', 'C4',
    #          'C5', 'C6', 'C7', 'C8', 'C9', 'D0', 'D01', 'D02', 'D03', 'D04', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7',
    #          'D8', 'D9', 'E0', 'E01', 'E02', 'E03', 'E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'F0', 'F01', 'F02', 'F1', 'F2',
    #          'F3', 'F4', 'F5', 'F6', 'G0', 'G01', 'G02', 'G1', 'G2', 'G3', 'H0', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
    #          'H7', 'H8', 'I0', 'I1', 'I2', 'I3', 'J0', 'J01', 'J08', 'J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8',
    #          'K0', 'K1', 'K2', 'K3', 'K4', 'L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9', 'M0', 'M1', 'M2',
    #          'M3', 'M4', 'M5', 'N0', 'N01', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9', 'O0', 'O1', 'O2',
    #          'O3', 'O4', 'O5', 'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'Q0', 'Q01', 'Q02', 'Q1', 'Q2', 'Q3', 'Q4', 'Q5',
    #          'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'Y0', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y6', 'Y7', 'Y8', 'Y9', 'Z0', 'Z1',
    #          'Z2', 'Z3']
    codes = ['A0']

    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum):
        return self.fetch_records(start_date, end_date)

    # For each code, go through each page and call fetch_page_results on that page, then call fetch_work on each work
    def fetch_records(self, start_date, end_date):
        self.base_url.args['stype'] = 'desc'
        self.base_url.args['SortOrder'] = 'ab_approval_date'
        for code in self.codes:
            page_number = 0
            self.base_url.args['code'] = code
            while True:
                page_number += 1
                self.base_url.args['npage'] = page_number
                try:
                    urls = self.fetch_page_results(self.base_url, start_date, end_date)
                except NoPagesLeft:
                    break
                for url in urls:
                    work = self.fetch_work('https://papers.ssrn.com/sol3/' + url)
                    yield work['URL'], work

    # Fetch the list of work urls on a single result page and return results within date range
    def fetch_page_results(self, url, start_date, end_date):
        r = self.requests.get(url.url)
        results = BeautifulSoup(r.text, 'html.parser').select('font > strong > a')[1:]
        if not results:
            raise NoPagesLeft
        return self.check_result_dates(results, start_date, end_date)

    # Find the works which are within the specified date range
    def check_result_dates(self, soup, start_date, end_date):
        date_checked_results = []
        for result in soup:
            # This is the element after the one that says 'Date posted: '
            date_string = result.parent.parent.parent.select('font > i')[0].next_sibling
            date_object = pendulum.strptime(date_string, '%B %d, %Y')
            if date_object < start_date:
                break
            if date_object > end_date:
                continue
            date_checked_results.append(result)
        return [url.get('href') for url in date_checked_results]

    def fetch_work(self, url):
        r = self.requests.get(url)
        #TODO: verify it still works
        # soup = BeautifulSoup(r.text, 'html.parser').find(id='outerLightBlue')
        soup = BeautifulSoup(r.text, 'html.parser')
        authors = soup.select('#innerWhite a h2')
        dates = soup.select('.dateInfo > font')
        data = {
            'URL': url,
            'Title': soup.h1.text,
            'Authors': {author.text: [author.parent['href'], author.parent.next_sibling.next_sibling]
                       for author in authors},
            'Journal': soup.select('#innerWhite i')[0].text if soup.select('#innerWhite i') else None,
            'Abstract': soup.find(id='abstract').text,
            'Date posted': dates[0].text,
            'Date revised': dates[1].text if len(dates) > 1 else None,
            'Citation': soup.select('#suggestedCitation .simField')[0].text,
        }
        # For page number and keywords:
        for p in soup.select('p > font > b'):
            data[p.text.replace(':', '')] = p.next_sibling.replace(' ', '')
        # data['Contact'] = {person.h5.text: person.div.text for person in soup.select('#affiliations td')}
        contacts = {}
        for person in soup.select('#affiliations td'):
            contacts[person.h5.text] = person.div.text if person.div and person.h5 else 'sdf'
        data['Contacts'] = contacts
        # for person in soup.select('#affiliations td'):
        #
        # 'Contact': {person.h5.text: person.div.text for person in }

        return data

# TODO: delete page.html


class NoPagesLeft(Exception):
    pass
