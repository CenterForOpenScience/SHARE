# Generated by Django 3.2.5 on 2023-07-26 12:12

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trove', '0002_indexcard_deleted'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourceidentifier',
            name='raw_iri_list',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), default=list, size=None),
        ),
    ]
