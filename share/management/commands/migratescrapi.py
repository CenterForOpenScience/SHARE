import os

from collections import OrderedDict
from hashlib import sha256

import arrow

from django.db import connections
from django.apps import apps
from django.core.management.base import BaseCommand

from share.models import RawData

# setup the migration source db connection
connections._databases['migration_source'] = {
  'ENGINE': 'django.db.backends.postgresql_psycopg2',
  'NAME': os.environ.get('SCRAPI_DATABASE_NAME', 'scrapi_prod'),
  'USER': os.environ.get('SCRAPI_DATABASE_USER', 'postgres'),
  'PASSWORD': os.environ.get('SCRAPI_DATABASE_PASSWORD', '...'),
  'HOST': os.environ.get('SCRAPI_DATABASE_HOST', 'localhost'),
  'PORT': os.environ.get('SCRAPI_DATABASE_PORT', '54321'),
}

# override model datetime field defaults, allows for migrated data insertion
RawData._meta.get_field('date_seen').auto_now = False
RawData._meta.get_field('date_harvested').auto_now_add = False


class Command(BaseCommand):
    can_import_settings = True

    source_map = OrderedDict(sorted({
        'addis_ababa': 'et.addisababa',
        'arxiv_oai': 'org.arxiv',
        'asu': 'edu.asu',
        'bhl': 'org.bhl',
        'biomedcentral': 'com.biomedcentral',
        'boise_state': 'edu.boisestate',
        'calhoun': 'edu.calhoun',
        'calpoly': 'edu.calpoly',
        'caltech': 'edu.caltech',
        'cambridge': 'uk.cambridge',
        'chapman': 'edu.chapman',
        # 'citeseerx': '...',
        # 'clinicaltrials': '...',
        # 'cmu': '...',
        'cogprints': 'org.cogprints',
        # 'colostate': '...',
        # 'columbia': '...',
        # 'crossref': '...',
        # 'csir': '...',
        # 'csuohio': '...',
        # 'cuny': '...',
        # 'cuscholar': '...',
        # 'cyberleninka': '...',
        # 'dailyssrn': '...',
        # 'dash': '...',
        # 'datacite': '...',
        # 'dataone': '...',
        # 'digitalhoward': '...',
        # 'doepages': '...',
        # 'dryad': '...',
        # 'duke': '...',
        # 'elife': '...',
        # 'erudit': '...',
        'figshare': 'com.figshare',
        # 'fit': '...',
        # 'ghent': '...',
        # 'hacettepe': '...',
        # 'harvarddataverse': '...',
        # 'huskiecommons': '...',
        # 'iastate': '...',
        # 'icpsr': '...',
        # 'iowaresearch': '...',
        # 'iu': '...',
        # 'iwu_commons': '...',
        # 'kent': '...',
        # 'krex': '...',
        # 'lshtm': '...',
        # 'lwbin': '...',
        # 'mason': '...',
        # 'mblwhoilibrary': '...',
        # 'mit': '...',
        # 'mizzou': '...',
        # 'mla': '...',
        # 'nature': '...',
        # 'ncar': '...',
        # 'neurovault': '...',
        # 'nih': '...',
        # 'nist': '...',
        # 'nku': '...',
        'noaa_nodc': 'gov.nodc',
        'npp_ksu': 'org.newprairiepress',
        # 'nsfawards': '...',
        # 'oaktrust': '...',
        # 'opensiuc': '...',
        # 'osf': '...',
        # 'pcom': '...',
        # 'pcurio': '...',
        # 'pdxscholar': '...',
        # 'plos': '...',
        # 'pubmedcentral': '...',
        # 'purdue': '...',
        # 'rcaap': '...',
        # 'scholarsarchiveosu': '...',
        # 'scholarsbank': '...',
        # 'scholarscompass_vcu': '...',
        # 'scholarsphere': '...',
        # 'scholarworks_umass': '...',
        # 'scitech': '...',
        # 'shareok': '...',
        # 'sldr': '...',
        # 'smithsonian': '...',
        # 'spdataverse': '...',
        # 'springer': '...',
        # 'stcloud': '...',
        # 'tdar': '...',
        # 'texasstate': '...',
        # 'triceratops': '...',
        # 'trinity': '...',
        # 'ucescholarship': '...',
        # 'ucsd': '...',
        # 'udc': '...',
        # 'udel': '...',
        # 'uhawaii': '...',
        # 'uiucideals': '...',
        # 'ukansas': '...',
        # 'uky': '...',
        # 'umassmed': '...',
        # 'umich': '...',
        # 'umontreal': '...',
        # 'uncg': '...',
        # 'unl_digitalcommons': '...',
        # 'uow': '...',
        # 'upennsylvania': '...',
        # 'usgs': '...',
        # 'u_south_fl': '...',
        # 'utaustin': '...',
        # 'ut_chattanooga': '...',
        # 'utktrace': '...',
        # 'uwashington': '...',
        # 'uwo': '...',
        # 'valposcholar': '...',
        # 'vtech': '...',
        # 'wash_state_u': '...',
        # 'waynestate': '...',
        # 'wustlopenscholarship': '...',
        # 'zenodo': '...',
    }.items()))

    def do_migration(self, source: str, app_label: str):
        config = apps.get_app_config(app_label)

        # This is required to populate the connection object properly
        connection = connections['migration_source']
        if connection.connection is None:
            connection.cursor()

        print('{} -> {}'.format(source, app_label))
        with connection.connection.cursor('scrapi_migration', withhold=True) as cursor:
            cursor.execute("""SELECT "docID", raw FROM webview_document WHERE source = '{source}';""".format(source=source))
            record_count = 0
            records = cursor.fetchmany(size=cursor.itersize)
            while records:
                bulk = []
                for (doc_id, raw) in records:
                    harvest_finished = arrow.get(raw['timestamps']['harvestFinished'])
                    data = raw['doc'].encode()
                    bulk.append(RawData(
                        source=config.user,
                        provider_doc_id=doc_id,
                        sha256=sha256(data).hexdigest(),
                        data=data,
                        date_seen=harvest_finished.datetime,
                        date_harvested=harvest_finished.datetime,
                    ))
                RawData.objects.bulk_create(bulk)
                record_count += len(records)
                print(record_count)
                records = cursor.fetchmany(size=cursor.itersize)

    def handle(self, *args, **options):
        for key in self.source_map.keys():
            self.do_migration(key, self.source_map.get(key))
