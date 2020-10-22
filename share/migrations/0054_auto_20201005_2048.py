# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2020-10-05 20:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import share.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0053_auto_20180419_2033'),
    ]

    operations = [
        migrations.CreateModel(
            name='CachedElasticDoc',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('doc_format', models.CharField(choices=[('BC', 'Back-compatible'), ('TR', 'Trove-style')], max_length=2)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('elastic_doc', share.models.fields.DateTimeAwareJSONField()),
                ('suid', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='share.SourceUniqueIdentifier')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='cachedelasticdoc',
            unique_together=set([('suid', 'doc_format')]),
        ),
    ]
