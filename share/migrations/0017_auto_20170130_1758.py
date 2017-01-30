# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-01-30 17:58
from __future__ import unicode_literals

from django.db import migrations
import share.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0016_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='award',
            name='uri',
            field=share.models.fields.ShareURLField(null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='awardversion',
            name='uri',
            field=share.models.fields.ShareURLField(null=True),
        ),
    ]
