# Generated by Django 3.2.5 on 2021-07-12 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0059_fmr_date_modified_index'),
    ]

    # no-op updates for Django 3.2 -- none of these operations generate any SQL:
    #   - replace `NullBooleanField()` with `BooleanField(null=True)`
    #   - replace postgres-specific `JSONField` with new `django.db.models.JSONField`
    operations = [
        migrations.AlterField(
            model_name='harvestjob',
            name='claimed',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='ingestjob',
            name='claimed',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='rawdatum',
            name='no_output',
            field=models.BooleanField(help_text='Indicates that this RawDatum resulted in an empty graph when transformed. This allows the RawDataJanitor to find records that have not been processed. Records that result in an empty graph will not have a NormalizedData associated with them, which would otherwise look like data that has not yet been processed.', null=True),
        ),
        migrations.AlterField(
            model_name='sourceconfig',
            name='harvester_kwargs',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sourceconfig',
            name='regulator_steps',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sourceconfig',
            name='transformer_kwargs',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
