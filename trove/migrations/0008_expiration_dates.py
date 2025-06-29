# Generated by Django 3.2.25 on 2025-06-09 15:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trove', '0007_rawdata_fks_do_nothing'),
    ]

    operations = [
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
        migrations.AddIndex(
            model_name='latestindexcardrdf',
            index=models.Index(fields=['expiration_date'], name='trove_lates_expirat_92ac89_idx'),
        ),
        migrations.AddIndex(
            model_name='supplementaryindexcardrdf',
            index=models.Index(fields=['expiration_date'], name='trove_suppl_expirat_3ea6e1_idx'),
        ),
    ]
