# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-09 19:28
from __future__ import unicode_literals

from django.db import migrations
import share.robot


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0001_initial'),
        ('djcelery', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            code=share.robot.RobotScheduleMigration('org.zenodo.datacite'),
        ),
    ]
