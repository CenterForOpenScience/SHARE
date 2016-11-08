from django.core.management.base import BaseCommand
from django.db import connection
from django.db import transaction


class Command(BaseCommand):

    def handle(self, *args, **options):
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute('''
                    DO $$
                    DECLARE
                    tname TEXT;
                    keep  TEXT [] = ARRAY [];
                    BEGIN FOR tname IN (SELECT table_name
                                        FROM information_schem.tables
                                        WHERE table_schema = 'public' AND NOT (table_name = ANY (keep))
                                            AND table_name LIKE 'share_%'
                                            AND NOT table_name LIKE 'share_shareuser%'
                                        LOOP
                                        RAISE NOTICE 'DROP TABLE % CASCADE', tname;
                    EXECUTE 'DROP TABLE ' || tname || ' CASCADE';
                    END LOOP;
                    END;
                    $$
                ''')
                c.execute("DELETE FROM django_migrations WHERE app = 'share';")
