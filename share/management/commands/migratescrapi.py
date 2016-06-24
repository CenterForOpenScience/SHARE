from collections import OrderedDict
from hashlib import sha256

from django.db import connections
from django.apps import apps
from django.core.management.base import BaseCommand

from share.models import RawData


class Command(BaseCommand):
    can_import_settings = True

    source_map = OrderedDict(sorted({
        # 'addis_ababa': '...',
        'arxiv_oai': 'org.arxiv',
        # 'asu': '...',
        # 'bhl': '...',
        # 'biomedcentral': '...',
        # 'boise_state': '...',
        # 'calhoun': '...',
        # 'calpoly': '...',
        'caltech': 'edu.caltech',
        'cambridge': 'uk.ac.cambridge',
        # 'chapman': '...',
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
        # 'noaa_nodc': '...',
        # 'npp_ksu': '...',
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

    def do_migration(self, source, app_label):
        print('{} -> {}'.format(source, app_label))

        config = apps.get_app_config(app_label)
        harvester = config.harvester(config)

        # This is required to populate the connection object properly
        connection = connections['scrapi']
        if connection.connection is None:
            connection.cursor()

        with connection.connection.cursor('scrapi_migration', withhold=True) as cursor:
            cursor.execute("""SELECT "docID", raw FROM webview_document WHERE source = '{source}';""".format(source=source))

            records = cursor.fetchmany(size=cursor.itersize)
            while records:
                print('records:', len(records))
                bulk = []
                for (doc_id, raw) in records:
                    data = raw['doc'].encode()
                    bulk.append(RawData(
                        source=harvester.source,
                        provider_doc_id=doc_id,
                        sha256=sha256(data).hexdigest(),
                        data=data,
                    ))
                RawData.objects.bulk_create(bulk)
                records = cursor.fetchmany(size=cursor.itersize)

                # TODO: allow idempotent catch up w/ upsert and logging
                # if created:
                    #     logger.debug('Newly created RawData for document {} from {}'.format(doc_id, source))
                    #     NormalizationQueue(data=rd).save()
                    # else:
                    #     logger.debug('Saw exact copy of document {} from {}'.format(doc_id, source))

                    # rd.save()  # Force timestamps to update
                    # return rd

    def handle(self, *args, **options):
        for key in self.source_map.keys():
            self.do_migration(key, self.source_map.get(key))
