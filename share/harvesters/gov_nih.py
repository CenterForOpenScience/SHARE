import re
import logging

from bs4 import BeautifulSoup
from datetime import date, timedelta
from dateutil.parser import parse
from io import BytesIO
from lxml import etree
from zipfile import ZipFile

from share.harvest import BaseHarvester


logger = logging.getLogger(__name__)


class NIHHarvester(BaseHarvester):
    """
    h/t to @fabianvf for this harvester.
    """
    VERSION = 1

    namespaces = {'xsi': "http://www.w3.org/2001/XMLSchema-instance"}

    def do_harvest(self, start_date, end_date, table_url):
        end_date = end_date.date()
        start_date = start_date.date()
        logger.info('Harvesting NIH %s - %s', start_date, end_date)

        # get ExPORTER page html and rows storing records
        html = self.requests.get(table_url).content
        soup = BeautifulSoup(html, 'lxml')
        table = soup.find('table', id="ContentPlaceHolder1_ProjectData_dgProjectData")
        rows = table.find_all('tr', class_="row_bg")
        urls = [i for i in self.construct_urls(self.config.base_url, start_date, end_date, rows)]
        logger.debug('Found %d urls to grab', len(urls))
        records = self.xml_records(self.get_xml_files(urls))

        for record in records:
            doc = etree.tostring(record)
            doc_id = record.xpath('.//APPLICATION_ID/node()', namespaces=self.namespaces)[0]
            yield (doc_id, doc)

    def daterange(self, start_date, end_date):
        """
        Get all the dates between the start_date and the end_date
        """
        for ordinal in range(start_date.toordinal(), end_date.toordinal()):
            yield date.fromordinal(ordinal)

    def get_days_of_week(self, start_date, end_date, day_of_week):
        """
        First convert start_date and end_date to have the day of week we require.
        Then get all the dates of the specified day of week between the start_date and end_date.
        """
        start_date = start_date - timedelta(days=(start_date.weekday() - day_of_week))
        end_date = end_date - timedelta(days=(end_date.weekday() - day_of_week))

        for ordinal in range(start_date.toordinal(), end_date.toordinal() + 1):
            if date.fromordinal(ordinal).weekday() == day_of_week:
                yield date.fromordinal(ordinal)

    def get_fiscal_year(self, mydate=date.today()):
        """
        Return the current fiscal year. Each fiscal year starts on October 1
        """
        if mydate.month < 10:
            return mydate.year
        return mydate.year + 1

    def get_fiscal_years(self, dates):
        """
        Given a range of dates, get unique fiscal years
        """
        return tuple(set(map(self.get_fiscal_year, dates)))

    def parse_month_column(self, month_column, day_of_week):
        """
        Given a month column string, return the date of a day (Monday by default) of that week
        An example of a month column string: September 2015, WEEK 1
        """
        month_year, week = iter(map(lambda x: x.strip(), month_column.split(',')))
        first_day = parse('1 ' + month_year)
        first_day -= timedelta(days=(first_day.weekday() - day_of_week + 7 * (1 if first_day.weekday() - day_of_week <= 0 else 0)))
        week = int(re.search('.*([0-9]{1,2})', week).group(1))
        mydate = first_day + timedelta(week * 7)
        return mydate.date()

    def parse_row(self, row, day_of_week):
        """
        Get a row of the ExPORTER table, return the date of a day (Monday by default) of that week, the fiscal year,
        and the url of the xml file
        To keep the format consistent, if the record is from previous fiscal years, None is returned
        """
        row_text = list(map(lambda x: x.text.strip('\t\n\r').strip('</td>'), row))
        row_text = list(map(lambda x: x.strip(), row_text))
        month_column = row_text[1]
        fiscal_year = int(row_text[2])
        url = row[3].find('a').get('href')

        if month_column.lower() == u"all":
            return (None, fiscal_year, url)
        elif re.match('[A-Za-z\s]* [0-9]{4}, WEEK \d+', month_column):
            date = self.parse_month_column(month_column, day_of_week)
            return (date, fiscal_year, url)
        else:
            raise ValueError('Unrecognized month column format: "{}"'.format(month_column))

    def parse_rows(self, rows, day_of_week):
        """
        A generator to parse all the rows
        """
        for row in rows:
            yield self.parse_row(row('td'), day_of_week)

    def construct_urls(self, url, start_date, end_date, rows, day_of_week=0):
        """
        Given date range, constructs urls of corresponded XML files.
        """
        dates = [i for i in self.get_days_of_week(start_date, end_date, day_of_week)]
        fiscal_years = self.get_fiscal_years(dates)
        for data in self.parse_rows(rows, day_of_week):
            if data[0] in dates or (data[0] is None and data[1] in fiscal_years):
                yield ''.join([self.config.base_url, data[2]])

    def xml_records(self, files):
        for xml_file in files:
            # Avoids eating all available memory. Read one row at a time.
            for _, record in etree.iterparse(xml_file, tag='row'):
                yield record
                # Saw this on SO. claims to save more memory.
                # Probably does, lxml might be building one giant tree.
                record.clear()

    def get_xml_files(self, urls):
        for zip_url in urls:
            logger.info('Fetching URL %s', zip_url)
            data = self.requests.get(zip_url)
            zipfile = ZipFile(BytesIO(data.content))
            with zipfile.open(zipfile.namelist()[0], 'r') as f:
                # NOTE: reading the entire file in at once can
                # take up A LOT of memory. Use lxml's iterparse.
                yield f
