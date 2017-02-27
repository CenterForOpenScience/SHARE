import logging
import dateutil

from bs4 import BeautifulSoup
from furl import furl
import pendulum

from share.harvest import BaseHarvester

logger = logging.getLogger('__name__')


class AgEconHarvester(BaseHarvester):
    """
        Query Parameters:
            month (MM)
            year (YYYY)
            order (oldestFirst or None)
            starts_with (YYYY-MM-DD) they don't always have a day
            top (page number)

        Returns:
            Page with nearest date
            20 records/page
    """
    VERSION = '0.0.1'

    fields = {
        'title': 'title',
        'other titles': 'other_titles',
        'authors': 'authors',
        'editors': 'editors',
        'editors (email)': 'editors_email',
        'authors (email)': 'authors_email',
        'keywords': 'keywords',
        'jel codes': 'jel_codes',
        'issue date': 'issue_date',
        'series/report no.': 'series_report_number',
        'abstract': 'abstract',
        'uri': 'uri',
        'institution/association': 'institution_association',
        'identifiers': 'identifiers',
        'total pages': 'total_pages',
        'from page': 'from_page',
        'to page': 'to_page',
        'notes': 'notes',
        'collections:': 'collections',
    }

    # Request page with nearest date
    def do_harvest(self, start_date: pendulum.Pendulum, end_date: pendulum.Pendulum):
        return self.fetch_records(start_date, end_date)

    # Fetch the list of work urls on a single result page and return results within date range
    def fetch_records(self, start_date, end_date):
        logger.info('Harvesting % - %s', start_date, end_date)
        logger.debug('Fetching page %s', self.base_url)

        url = furl(self.config.base_url)
        url.args['starts_with'] = start_date
        r = self.requests.get(url.url)

        r.raise_for_status()
        within_date_range = True
        while within_date_range:
            document = BeautifulSoup(r.text, 'html.parser')
            results = document.select('a[href^="/handle/"]')[1:]
            for result in results:
                url = 'http://ageconsearch.umn.edu{}'.format(result.attrs['href'])
                work = self.fetch_work(url)
                date_status = self.check_record_date(work['issue_date'], start_date, end_date)

                # if date is > start_date continue and skip
                if date_status == 'after':
                    continue
                elif date_status == 'before':
                    within_date_range = False
                    return
                yield work['primary_identifier'], work

            r = self.requests.get('http://ageconsearch.umn.edu/{}'.format(document.find('a', string='Next page').attrs['href']))

    def check_record_date(self, issue_date, start_date, end_date):
        date_object = dateutil.parser.parse(issue_date, default=pendulum.create(2016, 1, 1))

        if date_object < start_date.start_of('day'):
            return 'before'
        if date_object > end_date.end_of('day'):
            return 'after'

        return 'within'

    # Pull data out of html
    def fetch_work(self, url):
        r = self.requests.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')
        data = {}

        data['primary_identifier'] = soup.find('code').text
        display_table = soup.find(class_='itemDisplayTable').find_all('tr')

        for row in display_table:
            label = row.find(class_='metadataFieldLabel').text.replace(':\xa0', '').lower()
            value_object = row.find(class_='metadataFieldValue')
            if value_object.string:
                value = value_object.string
            else:
                contents = []
                for content in value_object.contents:
                    contents.append(content.string or content)
                # Feels a little hacky
                value = [val for val in contents if val != BeautifulSoup('<br/>', 'lxml').br]

            data[self.fields[label]] = value

        return data
