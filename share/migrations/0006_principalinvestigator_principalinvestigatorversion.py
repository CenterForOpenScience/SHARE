# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-11-02 17:55
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0005_auto_20161031_2245'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrincipalInvestigator',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('share.contributor',),
        ),
        migrations.CreateModel(
            name='PrincipalInvestigatorVersion',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('share.contributorversion',),
        ),
    ]
