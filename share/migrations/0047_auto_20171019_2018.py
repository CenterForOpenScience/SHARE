# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-19 20:18
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0046_auto_20170714_1547'),
    ]

    operations = [
        migrations.AlterField(
            model_name='source',
            name='user',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='sourceconfig',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source_configs', to='share.Source'),
        ),
    ]
