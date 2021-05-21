# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False  # CREATE INDEX CONCURRENTLY cannot be run in a txn

    dependencies = [
        ('share', '0001_squashed_0058_big_rend'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                # tell Django we're adding an index
                migrations.AddIndex(
                    model_name='formattedmetadatarecord',
                    index=models.Index(fields=['date_modified'], name=['fmr_date_modified_index']),
                ),
            ],
            database_operations=[
                # add the index without locking
                # (if we were using Django 3, would use
                #  django.contrib.postgres.operations.AddIndexConcurrently)
                migrations.RunSQL([
                    'CREATE INDEX CONCURRENTLY "fmr_date_modified_index" ON "share_formattedmetadatarecord" ("date_modified");',
                ], [
                    'DROP INDEX IF EXISTS "fmr_date_modified_index";'
                ])
            ]
        )
    ]
