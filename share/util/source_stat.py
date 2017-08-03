import logging

import requests
from furl import furl
from lxml import etree
import pendulum

from share.models import SourceStat
from share.models import SourceConfig

logger = logging.getLogger(__name__)


class SourceStatus:

    ACCEPTABLE_STATUS_CODES = (200, 401, 403)

    def __init__(self, config_id):
        self.source_config = SourceConfig.objects.get(pk=config_id)

    def assert_no_exception(self, url, timeout=15.0):
        try:
            r = requests.get(url, timeout=timeout)
        # except all exception and log
        except Exception as e:
            logger.warning('Exception received from source: %s', e)
            return (None, e)
        return (r, None)

    def get_source_stats(self):
        base_url_config = self.source_config.base_url
        response_elapsed_time = 0
        response_status_code = None
        grade = 10

        response, response_exception = self.assert_no_exception(base_url_config)

        if response is not None:
            response_elapsed_time = response.elapsed.total_seconds()
            response_status_code = response.status_code
        if response_status_code not in self.ACCEPTABLE_STATUS_CODES or response_elapsed_time == 0:
            grade = 0
        if response_elapsed_time > 1:
            grade = 5

        self.create_source_stat(
            earliest_datestamp_config=str(self.source_config.earliest_date) if self.source_config.earliest_date else None,
            base_url_config=base_url_config,
            response_status_code=response_status_code,
            response_elapsed_time=response_elapsed_time,
            response_exception=response_exception,
            grade=grade,
        )

    def create_source_stat(self, earliest_datestamp_source=None,
                           earliest_datestamps_match=True, base_url_source='',
                           base_urls_match=True, admin_note='', **kwargs):
        SourceStat.objects.create(
            config_id=self.source_config.id,

            earliest_datestamp_source=earliest_datestamp_source,
            earliest_datestamp_config=kwargs.pop('earliest_datestamp_config'),
            earliest_datestamps_match=earliest_datestamps_match,

            base_url_source=base_url_source,
            base_url_config=kwargs.pop('base_url_config'),
            base_urls_match=base_urls_match,

            response_status_code=kwargs.pop('response_status_code'),
            response_elapsed_time=kwargs.pop('response_elapsed_time'),
            response_exception=kwargs.pop('response_exception'),

            grade=kwargs.pop('grade'),
            admin_note=admin_note,
        )


class OAISourceStatus(SourceStatus):

    NAMESPACES = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ns0': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
    }

    # Known incorrect baseUrl:
    INCORRECT_BASE_URLS = {
        'https://biblio.ugent.be/oai': 'Listed baseURL is their homepage.',
        'http://purr.purdue.edu/oaipmh': 'Listed baseURL is their homepage.',
        'https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi': 'Listed baseURL is incorrect.',
        'https://mla.hcommons.org/deposits/oai/': 'isted baseURL is incorrect.',
        'http://oai.repec.org': 'Listed baseURL redirects.',
    }

    # Known incorrect earliestDatestamp (all emailed):
    INCORRECT_EARLIEST_DATESTAMP = {
        'edu.oaktrust.mods': 'Listed earliestDatestamp is the most recent datestamp.',
        'edu.scholarsarchiveosu.mods': 'Listed earliestDatestamp is 0011-01-01.',
        'edu.uwashington.mods': 'Listed earliestDatestamp is 2083-03-01.',
        'gov.nodc': 'Listed earliestDatestamp is 1996-10-09.',
        'org.philpapers': 'Listed earliestDatestamp is 1990-01-01T00:00:00Z.',
        'org.ttu.mods': 'Listed earliestDatestamp is 1989-05-01T05:00:00Z.',
        'edu.umich.mods': 'Listed earliestDatestamp is 1983-01-01T05:00:00Z.',
        'edu.citeseerx': 'Listed earliestDatestamp is 1970-01-01.',
        'br.pcurio': 'Listed earliestDatestamp is 1970-01-01.',
        'edu.vtech.mods': 'Listed earliestDatestamp is 1900-02-02T05:00:00Z.',
        'edu.icpsr': 'Listed earliestDatestamp is 01-01-1900',
        'pt.rcaap': 'Listed earliestDatestamp is 1900-01-01T00:00:00Z.',
        'com.nature': 'Listed earliestDatestamp is 1869-11-04.',
    }

    def get_field_from_identify(self, response, field):
        # TODO: record which sources are providing invalid XML i.e, fail without recover=True
        parsed = etree.fromstring(response.content, parser=etree.XMLParser(recover=True))
        return parsed.xpath('//ns0:Identify/ns0:{}'.format(field), namespaces=self.NAMESPACES)[0].text

    def get_source_stats(self):
        base_url_config = self.source_config.base_url
        base_url_source = ''
        base_urls_match = False
        earliest_datestamp_config = str(self.source_config.earliest_date) if self.source_config.earliest_date else None
        earliest_datestamp_source = None
        earliest_datestamps_match = False
        response_elapsed_time = 0
        response_status_code = None
        admin_note = ''
        grade = 10

        response, response_exception = self.assert_no_exception(furl(base_url_config).set({'verb': 'Identify'}).url)

        if response is not None:
            response_elapsed_time = response.elapsed.total_seconds()
            response_status_code = response.status_code
        if response:
            base_url_source = self.get_field_from_identify(response, 'baseURL')
            # ignores http vs https
            if len(base_url_source.split('://', 1)) > 1:
                base_urls_match = base_url_source.split('://', 1)[1] == base_url_config.split('://', 1)[1]
            else:
                logger.warning('Source baseURL is improper: %s', base_url_source)

            if base_url_config in self.INCORRECT_BASE_URLS:
                admin_note = self.INCORRECT_BASE_URLS[base_url_config]
            if self.source_config.label in self.INCORRECT_EARLIEST_DATESTAMP:
                admin_note = ' '.join(admin_note, self.INCORRECT_EARLIEST_DATESTAMP[self.source_config.label]) if admin_note else self.INCORRECT_EARLIEST_DATESTAMP[self.source_config.label]

            earliest_datestamp_identify = self.get_field_from_identify(response, 'earliestDatestamp')
            earliest_datestamp_source = pendulum.parse(earliest_datestamp_identify).to_date_string() if earliest_datestamp_identify else None
            earliest_datestamps_match = earliest_datestamp_config == earliest_datestamp_source

        if response_status_code not in self.ACCEPTABLE_STATUS_CODES or response_elapsed_time == 0:
            grade = 0
        if response_elapsed_time > 1:
            grade = 5
        if not earliest_datestamps_match:
            if self.source_config.label in self.INCORRECT_EARLIEST_DATESTAMP:
                grade = 5
            else:
                grade = 0
        if not base_urls_match:
            if base_url_config in self.INCORRECT_BASE_URLS:
                grade = 5
            else:
                grade = 0

        self.create_source_stat(
            earliest_datestamp_source=earliest_datestamp_source,
            earliest_datestamp_config=earliest_datestamp_config,
            earliest_datestamps_match=earliest_datestamps_match,

            base_url_source=base_url_source,
            base_url_config=base_url_config,
            base_urls_match=base_urls_match,

            response_status_code=response_status_code,
            response_elapsed_time=response_elapsed_time,
            response_exception=response_exception,

            grade=grade,
            admin_note=admin_note,
        )
