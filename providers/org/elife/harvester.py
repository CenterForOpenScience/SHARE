import logging

from furl import furl

from itertools import chain

from lxml import etree

from share.harvest.harvester import Harvester


logger = logging.getLogger(__name__)


class ELifeHarvester(Harvester):

    BASE_DATA_URL = 'https://raw.githubusercontent.com/elifesciences/elife-article-xml/master/{}'
    BASE_URL = 'https://api.github.com/repos/elifesciences/elife-article-xml/commits{}'

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()

        shas = self.fetch_commits(start_date, end_date)

        file_names = list(chain.from_iterable([
            self.fetch_file_names(sha)
            for sha in shas
        ]))

        logger.info("There are {} record urls to harvest - this may take a while... ".format(len(file_names)))

        xml_records = [
            self.fetch_xml(file_name)
            for file_name in filter(lambda file_name: file_name.endswith('.xml'), file_names)
        ]

        for record in xml_records:
            doc = etree.tostring(record)
            doc_id = record.xpath('//article-id[@*]')[0].text
            yield (doc_id, doc)

    def fetch_commits(self, start_date, end_date):
        page = 0
        url = self.BASE_URL.format('?')
        response = self.requests.get(furl(url).set(query_params={
            'since': start_date.isoformat(),
            'until': end_date.isoformat(),
            'page': page,
            'per_page': 100
        }).url)

        commits = response.json()
        shas = [c['sha'] for c in commits]
        page += 1

        while len(commits) == 100:
            response = self.requests.get(furl(url).set(query_params={
                'since': start_date.isoformat(),
                'until': end_date.isoformat(),
                'page': page,
                'per_page': 100
            }).url)

            commits = response.json()
            shas = shas + [c['sha'] for c in commits]
            page += 1

        return shas

    def fetch_file_names(self, sha):
        page = 0
        url = self.BASE_URL.format('/{}'.format(sha))
        response = self.requests.get(furl(url).set(query_params={
            'page': page,
            'per_page': 100
        }))

        files = response.json()['files']
        file_names = [file['filename'] for file in files]

        while len(files) == 100:
            response = self.requests.get(furl(url).set(query_params={
                'page': page,
                'per_page': 100
            }))

            files = response.json()['files']
            file_names = file_names + [file['filename'] for file in files]
            page += 1

        return file_names

    def fetch_xml(self, file_name):
        resp = self.requests.get(self.BASE_DATA_URL.format(file_name))
        xml = etree.XML(resp.content)
        return xml
