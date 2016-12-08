import os

from collections import OrderedDict
from hashlib import sha256

import pendulum

from django.db import connections, transaction
from django.apps import apps
from django.core.management.base import BaseCommand

from share.models import RawData

# setup the migration source db connection
connections._databases['migration_source'] = {
    'ENGINE': 'django.db.backends.postgresql',
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

    map = OrderedDict(sorted({
        'addis_ababa': 'et.edu.addis_ababa',
        'arxiv_oai': 'org.arxiv.oai',
        'asu': 'edu.asu',
        'bhl': 'org.bhl',
        'biomedcentral': 'com.biomedcentral',
        'boise_state': 'edu.boise_state',
        'calhoun': 'edu.calhoun',
        'calpoly': 'edu.calpoly',
        'caltech': 'edu.caltech',
        'cambridge': 'uk.cambridge',
        'chapman': 'edu.chapman',
        'citeseerx': 'edu.citeseerx',
        'clinicaltrials': 'gov.clinicaltrials',
        'cmu': 'edu.cmu',
        'cogprints': 'org.cogprints',
        'colostate': 'edu.colostate',
        'columbia': 'edu.columbia',
        'crossref': 'org.crossref',
        'csir': 'za.csir',
        'csuohio': 'edu.csuohio',
        'cuny': 'edu.cuny',
        'cuscholar': 'edu.cuscholar',
        'cyberleninka': 'ru.cyberleninka',
        'dailyssrn': 'com.dailyssrn',
        'dash': 'edu.dash',
        'datacite': 'org.datacite.oai',
        'dataone': 'org.dataone',
        'digitalhoward': 'edu.digitalhoward',
        'doepages': 'gov.doepages',
        'dryad': 'org.dryad',
        'duke': 'edu.duke',
        'elife': 'org.elife',
        'erudit': 'org.erudit',
        'figshare': 'com.figshare',
        'fit': 'edu.fit',
        'ghent': 'be.ghent',
        'hacettepe': 'tr.edu.hacettepe',
        'harvarddataverse': 'edu.harvarddataverse',
        'huskiecommons': 'edu.huskiecommons',
        'iastate': 'edu.iastate',
        'icpsr': 'edu.icpsr',
        'iowaresearch': 'edu.iowaresearch',
        'iu': 'edu.iu',
        'iwu_commons': 'edu.iwu_commons',
        'kent': 'edu.kent',
        'krex': 'edu.krex',
        'lshtm': 'uk.lshtm',
        'lwbin': 'ca.lwbin',
        'mason': 'edu.mason',
        'mblwhoilibrary': 'org.mblwhoilibrary',
        'mit': 'edu.mit',
        'mizzou': 'edu.mizzou',
        'mla': 'org.mla',
        'nature': 'com.nature',
        'ncar': 'org.ncar',
        'neurovault': 'org.neurovault',
        'nih': 'gov.nih',
        'nist': 'gov.nist',
        'nku': 'edu.nku',
        'noaa_nodc': 'gov.nodc',
        'npp_ksu': 'org.newprairiepress',
        'nsfawards': 'gov.nsfawards',
        'oaktrust': 'edu.oaktrust',
        'opensiuc': 'edu.opensiuc',
        'osf': 'io.osf',
        'pcom': 'edu.pcom',
        'pcurio': 'br.pcurio',
        'pdxscholar': 'edu.pdxscholar',
        'plos': 'org.plos',
        'pubmedcentral': 'gov.pubmedcentral',
        'purdue': 'edu.purdue',
        'rcaap': 'pt.rcaap',
        'scholarsarchiveosu': 'edu.scholarsarchiveosu',
        'scholarsbank': 'edu.scholarsbank',
        'scholarscompass_vcu': 'edu.scholarscompass_vcu',
        # 'scholarsphere': '...', - does not exist in scrapi
        'scholarworks_umass': 'edu.scholarworks_umass',
        'scitech': 'gov.scitech',
        'shareok': 'org.shareok',
        'sldr': 'org.sldr',
        'smithsonian': 'edu.smithsonian',
        'spdataverse': 'info.spdataverse',
        'springer': 'com.springer',
        'stcloud': 'edu.stcloud',
        'tdar': 'org.tdar',
        'texasstate': 'edu.texasstate',
        'triceratops': 'edu.triceratops',
        'trinity': 'edu.trinity',
        'u_south_fl': 'edu.u_south_fl',
        'ucescholarship': 'org.ucescholarship',
        'udc': 'edu.udc',
        'udel': 'edu.udel',
        'uhawaii': 'edu.uhawaii',
        'uiucideals': 'edu.uiucideals',
        'ukansas': 'edu.ukansas',
        'uky': 'edu.uky',
        'umassmed': 'edu.umassmed',
        'umich': 'edu.umich',
        'umontreal': 'ca.umontreal',
        'uncg': 'edu.uncg',
        'unl_digitalcommons': 'edu.unl_digitalcommons',
        'uow': 'au.uow',
        'upennsylvania': 'edu.upennsylvania',
        # 'ucsd': '...', - does not exist in scrapi
        'usgs': 'gov.usgs',
        'ut_chattanooga': 'edu.ut_chattanooga',
        'utaustin': 'edu.utaustin',
        'utktrace': 'edu.utktrace',
        'uwashington': 'edu.uwashington',
        'uwo': 'ca.uwo',
        'valposcholar': 'edu.valposcholar',
        'vtech': 'edu.vtech',
        'wash_state_u': 'edu.wash_state_u',
        'waynestate': 'edu.waynestate',
        'wustlopenscholarship': 'edu.wustlopenscholarship',
        'zenodo': 'org.zenodo',
    }.items()))

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Migrate all scrapi harvester')
        parser.add_argument('harvester', nargs='*', type=str, help='The name of the scrapi harvester(s) to migrate')

    def handle(self, *args, **options):
        if not options['harvester'] and options['all']:
            options['harvester'] = [k for k in self.map.keys()]

        if options['harvester']:
            connection = connections['migration_source']

            # This is required to populate the connection object properly
            if connection.connection is None:
                connection.cursor()

            for source in options['harvester']:
                target = self.map[source]
                config = apps.get_app_config(target)

                print('{} -> {}'.format(source, target))
                with transaction.atomic(using='migration_source'):
                    with connection.connection.cursor('scrapi_migration') as cursor:
                        cursor.execute(
                            """
                                SELECT "docID", raw
                                FROM webview_document
                                WHERE source = '{source}'
                            """.format(source=source)
                        )

                        with transaction.atomic():
                            record_count = 0
                            records = cursor.fetchmany(size=cursor.itersize)

                            while records:
                                bulk = []
                                for (doc_id, raw) in records:
                                    if raw is None or raw == 'null' or raw['timestamps'] is None or raw['timestamps']['harvestFinished'] is None:
                                        print('{} -> {}: {} : raw is null'.format(source, target, doc_id))
                                        continue
                                    harvest_finished = pendulum.parse(raw['timestamps']['harvestFinished'])
                                    data = raw['doc'].encode()
                                    bulk.append(RawData(
                                        source=config.user,
                                        app_label=config.label,
                                        provider_doc_id=doc_id,
                                        sha256=sha256(data).hexdigest(),
                                        data=data,
                                        date_seen=harvest_finished.datetime,
                                        date_harvested=harvest_finished.datetime,
                                    ))
                                RawData.objects.bulk_create(bulk)
                                record_count += len(records)
                                print('{} -> {}: {}'.format(source, target, record_count))
                                records = cursor.fetchmany(size=cursor.itersize)
