# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-01-18 15:11
from __future__ import unicode_literals

from django.db import migrations
import share.robot


class Migration(migrations.Migration):

    dependencies = [
        ('tr.edu.hacettepe', '0001_initial'),
        ('share', '0015_store_favicons'),
    ]

    operations = [
        migrations.RunPython(
            code=share.robot.RobotFaviconMigration('tr.edu.hacettepe'),
        ),
    ]
