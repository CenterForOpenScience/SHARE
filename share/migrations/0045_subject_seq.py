# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-14 13:33
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0044_merge_20170628_1811'),
    ]

    operations = [
        # Resync the subject PK sequence with the table.
        # An old load script manually assigned ids.
        migrations.RunSQL('''
            SELECT setval('share_subject_id_seq', (SELECT MAX(id) FROM share_subject));
        '''),
        # The script also created a 0 PK that needs to be updated
        migrations.RunSQL('''
            -- Disable our neato trigger(s)
            ALTER TABLE share_subject DISABLE TRIGGER USER;

            -- Fix the messed up key (Yay ON UDATE CASCADE)
            UPDATE share_subject SET id = nextval('share_subject_id_seq') WHERE id = 0;

            -- Repoint any changes
            UPDATE share_change
                SET target_id = currval('share_subject_id_seq')
            WHERE target_id = 0
            AND target_type_id = (
                -- MAX here just in case there happens to be two entries in production
                -- MAX, the latest, will be the correct one to use
                SELECT MAX(id) FROM django_content_type WHERE app_label = 'share' AND model = 'subject'
            );

            -- Have to commit to re-enable triggers
            COMMIT;
            BEGIN;
            ALTER TABLE share_subject ENABLE TRIGGER USER;

            -- No extra commit so django can commit
        '''),
    ]
