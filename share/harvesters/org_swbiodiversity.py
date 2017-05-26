import itertools
import re
import logging

from bs4 import BeautifulSoup, Comment

from share.harvest import BaseHarvester


logger = logging.getLogger(__name__)


class SWHarvester(BaseHarvester):
    """

    """
    VERSION = 1

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()
        logger.info('Harvesting swbiodiversity %s - %s', start_date, end_date)
        return self.fetch_records()
        # get ExPORTER page html and rows storing records

    def fetch_records(self):
        html = self.requests.get(self.kwargs['list_url'])
        html.raise_for_status()
        soup = BeautifulSoup(html.content, 'lxml')
        records = soup.find_all('a')
        record_list = []
        for record in records:
            record_content = re.findall('collid=(\d+)', record.get('href'))
            if record_content and record_content[0] not in record_list:
                record_list.append(record_content[0])
        total = len(record_list)

        logging.info('Found %d results from swbiodiversity', total)
        count = 0
        while count < 1:
            logger.info('On collection %d of %d (%d%%)', count, total, (count / total) * 100)
            identifier = record_list[count]
            html = self.requests.get(self.kwargs['list_url'] + '?collid=' + identifier)
            html.raise_for_status()
            soup = BeautifulSoup(html.content, 'lxml')

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

            record = soup.find(id='innertext')
            title = self.process_text(record.h1)
            start = record.div.div
            description = self.process_text(start)

            body = start.find_all_next(style='margin-top:5px;')
            body = list(map(self.process_text, body))

            data = {'title': title, 'description': description, 'identifier': identifier}

            for entry in body:

                if 'Contact:' in entry:
                    contact = entry.replace('Contact: ', '')
                    contact_email = contact[contact.find("(") + 1:contact.find(")")]
                    contact_name = contact.replace('(' + contact_email + ')', '').strip()
                    data['contact'] = {'name': contact_name, 'email': contact_email}

                if 'Collection Type:' in entry:
                    collection_type = entry.replace('Collection Type: ', '')
                    data['collection-type'] = collection_type

                if 'Management:' in entry:
                    management = entry.replace('Management: ', '')
                    data['management'] = management

                if 'Usage Rights:' in entry:
                    usage_rights = entry.replace('Usage Rights: ', '')
                    data['usage-rights'] = usage_rights

                if 'Access Rights' in entry or 'Rights Holder:' in entry:
                    access_rights = entry.replace('Access Rights: ', '').replace('Rights Holder: ', '')
                    data['access-rights'] = access_rights

            collection_statistics = start.find_all_next('li')
            collection_statistics = list(map(self.process_text, collection_statistics))
            data['collection-statistics'] = self.process_collection_stat(collection_statistics)

            count += 1
            yield identifier, data

    def process_text(self, text):
        return re.sub('<[^>]*>', '', str(text)).strip()

    def process_collection_stat(self, list):
        stat = {}
        for item in list:
            value = item.split()
            stat[item.replace(str(value[0]), '').strip()] = value[0]
        return stat
