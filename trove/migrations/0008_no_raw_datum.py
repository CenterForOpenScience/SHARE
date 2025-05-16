from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trove', '0007_rawdata_fks_do_nothing'),
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
        migrations.AddField(
            model_name='archivedindexcardrdf',
            name='expiration_date',
            field=models.DateField(blank=True, help_text='An (optional) date when this description will no longer be valid.', null=True),
        ),
        migrations.AddField(
            model_name='latestindexcardrdf',
            name='expiration_date',
            field=models.DateField(blank=True, help_text='An (optional) date when this description will no longer be valid.', null=True),
        ),
        migrations.AddField(
            model_name='supplementaryindexcardrdf',
            name='expiration_date',
            field=models.DateField(blank=True, help_text='An (optional) date when this description will no longer be valid.', null=True),
        ),
    ]
