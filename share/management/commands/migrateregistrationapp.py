import os
from concurrent import futures

import furl
import requests

from django.db import connections, transaction
from django.core.management.base import BaseCommand

from share.models import ShareUser
from share.models import ProviderRegistration


# setup the migration source db connection
connections._databases['migration_source'] = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': os.environ.get('PROVIDER_REGISTRATION_DATABASE_NAME', 'shareregistration'),
    'USER': os.environ.get('PROVIDER_REGISTRATION_DATABASE_USER', 'postgres'),
    'PASSWORD': os.environ.get('PROVIDER_REGISTRATION_DATABASE_PASSWORD', ''),
    'HOST': os.environ.get('PROVIDER_REGISTRATION_DATABASE_HOST', 'localhost'),
    'PORT': os.environ.get('PROVIDER_REGISTRATION_DATABASE_PORT', '5432'),
}


def push_data(pk, doc_id, record, source, token, base_url):
    print('Submitting ({}) {} for user {!r}'.format(pk, doc_id, source))
    resp = requests.post('{}/api/v1/share/data/'.format(base_url.rstrip('/')), data=record, headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(token)
    })
    resp.raise_for_status()
    return resp


class Command(BaseCommand):
    can_import_settings = True

    def add_arguments(self, parser):
        parser.add_argument('--records', help='Migrate pushed records', action='store_true')
        parser.add_argument('--registrations', help='Migrate registrations', action='store_true')
        parser.add_argument('--url', type=str, help='The base url for the SHARE push API', default='http://localhost:8000/')

    def handle(self, url, records, registrations, *args, **options):
        if registrations:
            self.migrate_registrations()
        if records:
            self.migrate_users(url=url)

    def migrate_registrations(self):
        system_user = ShareUser.objects.get(username='system')
        # Hack to allow setting submitted_at
        ProviderRegistration._meta.get_field('submitted_at').auto_now_add = False

        connection = connections['migration_source']
        # This is required to populate the connection object properly
        if connection.connection is None:
            connection.cursor()

        with connection.connection.cursor() as cursor:
            cursor.execute('''
                SELECT json_build_object(
                    'accepted_tos', CASE WHEN meta_tos AND meta_rights AND meta_privacy AND meta_sharing AND meta_license_cc0 THEN TRUE ELSE FALSE END
                    , 'registration_complete', registration_complete
                    , 'metadata_complete', metadata_complete
                    , 'active_provider', active_provider
                    , 'registration_date', registration_date
                    , 'contact_name', contact_name
                    , 'contact_email', contact_email
                    , 'name', provider_long_name
                    , 'description', description
                    , 'rate_limit', rate_limit
                    , 'api_docs', api_docs
                    , 'oai_provider', oai_provider
                    , 'url', base_url
                    , 'desk_contact', desk_contact
                    , 'approved_sets', approved_sets
                    , 'properties_list', property_list
                )
                FROM provider_registration_registrationinfo WHERE id IN (SELECT max(id) FROM provider_registration_registrationinfo GROUP BY contact_email);
                ''')
            while True:
                records = cursor.fetchmany(size=cursor.itersize)
                if not records:
                    break
                for (record, ) in records:
                    if (record['name'] == 'temp_value' or record['url'] == 'temp_value') or not (record['registration_complete'] and (record['metadata_complete'] or record['desk_contact'])):
                        print('Form not completed by {contact_name} <{contact_email}>. Skipping'.format(**record))
                        continue
                    if not record['accepted_tos']:
                        print('TOS not accepted by {contact_name} <{contact_email}>. Skipping'.format(**record))
                        continue

                    ProviderRegistration.objects.create(
                        status=ProviderRegistration.STATUS.implemented if record['active_provider'] else ProviderRegistration.STATUS.pending,
                        submitted_by=system_user,
                        submitted_at=record['registration_date'],

                        contact_name=record['contact_name'],
                        contact_email=record['contact_email'],
                        contact_affiliation='Interested Party',

                        direct_source=False,

                        source_name=record['name'],
                        source_description=record['description'],
                        source_rate_limit=record['rate_limit'],
                        source_documentation=record['api_docs'],
                        source_oai=record['oai_provider'],
                        source_base_url=record['url'],
                        source_additional_info='Desk Contact: {desk_contact}\nApproved sets: {approved_sets}\nProperties list: {properties_list}\n'.format(**record)
                    )

    def migrate_users(self, url):
        connection = connections['migration_source']
        # This is required to populate the connection object properly
        if connection.connection is None:
            connection.cursor()

        with connection.connection.cursor() as cursor:
            # Established?
            cursor.execute('''
                    SELECT
                    provider.id
                    , key
                    , url
                    , longname
                    , favicon_dataurl
                    FROM push_endpoint_provider AS provider
                        JOIN auth_user ON provider.user_id = auth_user.id
                        JOIN authtoken_token ON auth_user.id = authtoken_token.user_id
                    WHERE EXISTS(SELECT NULL FROM push_endpoint_pusheddata WHERE push_endpoint_pusheddata.provider_id = provider.id LIMIT 1)
                ''')
            providers = cursor.fetchall()

        sources = []
        with transaction.atomic():
            for (pk, apikey, base_url, longname, favicon_dataurl) in providers:
                start, *_, end = furl.furl(base_url).host.split('.')
                username = '{}.{}'.format(end, start)
                try:
                    source = ShareUser.objects.get(username=username)
                except ShareUser.DoesNotExist:
                    source = ShareUser.objects.create_user(username, long_title=longname, home_page=base_url, is_trusted=True)
                    source.set_unusable_password()
                    token = source.accesstoken_set.first()
                    token.token = apikey
                    token.save()

                print('Created new user {!r}'.format(source))
                sources.append((pk, source))

        with transaction.atomic(using='migration_source'):
            for pk, source in sources:
                token = source.accesstoken_set.first().token
                print('Loading documents for user {!r}'.format(source))

                with connection.connection.cursor('provider_migration') as cursor:
                    fs = []
                    cursor.execute('SELECT id, "docID", "jsonData" FROM push_endpoint_pusheddata WHERE provider_id = %s', (pk, ))
                    with futures.ThreadPoolExecutor(max_workers=20) as e:
                        while True:
                            records = cursor.fetchmany(size=cursor.itersize)
                            if not records:
                                break

                            for pk, doc_id, record in records:
                                fs.append(e.submit(push_data, pk, doc_id, record, source, token, url))

                        for fut in futures.wait(fs, return_when=futures.FIRST_EXCEPTION)[1]:
                            if fut.exception():
                                e.shutdown(wait=False)
                                raise fut.exception()
