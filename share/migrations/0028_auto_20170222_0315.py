# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-02-22 03:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0027_harvestlog_raw_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='harvestlog',
            name='raw_data',
        ),
        migrations.AlterField(
            model_name='rawdatum',
            name='logs',
            field=models.ManyToManyField(related_name='raw_data', to='share.HarvestLog'),
        ),
    ]
