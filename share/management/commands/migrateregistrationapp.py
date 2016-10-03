import os
from concurrent.futures import ThreadPoolExecutor

import furl
import requests

from django.db import connections, transaction
from django.core.management.base import BaseCommand

from share.models import ShareUser

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
        parser.add_argument('--url', type=str, help='The base url for the SHARE push API', default='http://localhost:8000/')

    def handle(self, *args, url=None, **options):
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
                    WHERE provider.established = TRUE;
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
                    cursor.execute('SELECT id, "docID", "jsonData" FROM push_endpoint_pusheddata WHERE provider_id = %s;', (pk, ))
                    with ThreadPoolExecutor() as e:
                        while True:
                            records = cursor.fetchmany(size=cursor.itersize)
                            if not records:
                                break

                            for pk, doc_id, record in records:
                                e.submit(push_data, pk, doc_id, record, source, token, url)
