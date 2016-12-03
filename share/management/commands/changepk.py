from django.core.management.base import BaseCommand
from django.db import connection
from django.db import transaction

from share.models import AbstractCreativeWork


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('old_pk', type=int, help='')
        parser.add_argument('new_pk', type=int, help='')

    def handle(self, old_pk, new_pk, *args, **options):
        tables = set(
            f.remote_field.model._meta.db_table
            for f in AbstractCreativeWork._meta.get_fields()
            if f.is_relation
            and not f.many_to_many
            and f.remote_field.model is not AbstractCreativeWork
            and getattr(f.remote_field.model, 'VersionModel', None)
        )
        tables.add(AbstractCreativeWork._meta.db_table)

        with transaction.atomic():
            with connection.cursor() as c:
                c.execute('\n'.join('ALTER TABLE {} DISABLE TRIGGER USER;'.format(table) for table in tables))

                for field in AbstractCreativeWork._meta.get_fields(include_hidden=True):
                    if not field.is_relation or field.many_to_many or not hasattr(field, 'field'):
                        continue
                    field = field.field
                    field.model.objects.select_for_update().filter(**{
                        field.name: old_pk
                    }).update(**{
                        field.name: new_pk
                    })

                for field in AbstractCreativeWork._meta.virtual_fields:
                    field.remote_field.model.objects.select_for_update().filter(**{
                        field.object_id_field_name: old_pk,
                    }).update(**{
                        field.object_id_field_name: new_pk,
                    })

                AbstractCreativeWork.objects.select_for_update().filter(id=old_pk).update(id=new_pk)
                AbstractCreativeWork.VersionModel.objects.select_for_update().filter(persistent_id=old_pk).update(persistent_id=new_pk)

                c.execute('\n'.join('ALTER TABLE {} ENABLE TRIGGER USER;'.format(table) for table in tables))
