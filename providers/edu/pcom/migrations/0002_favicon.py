# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-01-17 21:46
from __future__ import unicode_literals

from django.db import migrations
import share.robot


class Migration(migrations.Migration):

    dependencies = [
        ('edu.pcom', '0001_initial'),
        ('share', '0015_store_favicons'),
    ]

    operations = [
        migrations.RunPython(
            code=share.robot.RobotFaviconMigration('edu.pcom'),
        ),
    ]
