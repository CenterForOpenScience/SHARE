from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trove', '0008_expiration_dates'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='archivedindexcardrdf',
            name='trove_archivedindexcardrdf_uniq_archived_version',
        ),
        migrations.RemoveField(
            model_name='archivedindexcardrdf',
            name='from_raw_datum',
        ),
        migrations.RemoveField(
            model_name='latestindexcardrdf',
            name='from_raw_datum',
        ),
        migrations.RemoveField(
            model_name='supplementaryindexcardrdf',
            name='from_raw_datum',
        ),
    ]
