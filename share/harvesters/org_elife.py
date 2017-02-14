import time
import logging
import requests

from django.conf import settings

from furl import furl

from lxml import etree

from share.harvest import BaseHarvester


logger = logging.getLogger(__name__)


class ELifeHarvester(BaseHarvester):
    KEY = 'org.elife'
    VERSION = '0.0.1'

    BASE_DATA_URL = 'https://raw.githubusercontent.com/elifesciences/elife-article-xml/master/{}'
    BASE_URL = 'https://api.github.com/repos/elifesciences/elife-article-xml/commits{}'

    def request(self, *args, **kwargs):
        if settings.GITHUB_API_KEY:
            kwargs.setdefault('headers', {})['Authorization'] = 'token {}'.format(settings.GITHUB_API_KEY)

        while True:
            response = self.requests.get(*args, **kwargs)

            if int(response.headers.get('X-RateLimit-Remaining', 0)) == 0:
                reset = int(response.headers.get('X-RateLimit-Reset', time.time())) - time.time()
                logger.warning('Hit GitHub ratelimit sleeping for %s seconds', reset)
                time.sleep(reset)

            if response.status_code != 403:
                response.raise_for_status()
                return response

    def do_harvest(self, start_date, end_date):
        end_date = end_date.date()
        start_date = start_date.date()

        logger.info("The data for each record must be requested individually - this may take a while... ")

        for sha in self.fetch_commits(start_date, end_date):
            for file_name in self.fetch_file_names(sha):
                if not file_name.endswith('.xml'):
                    continue
                record = self.fetch_xml(file_name)
                if record is not None:
                    continue
                doc = etree.tostring(record)
                doc_id = record.xpath('//article-id[@*]')[0].text
                yield (doc_id, doc)

    def fetch_commits(self, start_date, end_date):
        page = -1
        url = self.BASE_URL.format('?')

        while True:
            page += 1
            response = self.request(furl(url).set(query_params={
                'since': start_date.isoformat(),
                'until': end_date.isoformat(),
                'page': page,
                'per_page': 100
            }).url)

            commits = response.json()
            for commit in commits:
                if commit.get('sha'):
                    yield commit['sha']

            if len(commits) != 100:
                break

    def fetch_file_names(self, sha):
        page = -1
        url = self.BASE_URL.format('/{}'.format(sha))

        while True:
            page += 1
            response = self.request(furl(url).set(query_params={
                'page': page,
                'per_page': 100
            }))

            files = response.json()['files']
            for f in files:
                yield f['filename']

            if len(files) != 100:
                break

    def fetch_xml(self, file_name):
        file_url = furl(self.BASE_DATA_URL.format(file_name))
        # Not using self.requests when getting the file contents because the eLife rate limit (1, 60) does not apply
        resp = requests.get(file_url.url)
        if resp.status_code == 404:
            logger.warning('Could not download file %s', file_name)
            return None
        resp.raise_for_status()
        xml = etree.XML(resp.content)
        return xml
