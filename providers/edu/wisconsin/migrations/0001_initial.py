# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-25 15:05
from __future__ import unicode_literals

from django.db import migrations
import share.robot


class Migration(migrations.Migration):

    dependencies = [
        ('djcelery', '0001_initial'),
        ('share', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            code=share.robot.RobotUserMigration('edu.wisconsin'),
        ),
        migrations.RunPython(
            code=share.robot.RobotOauthTokenMigration('edu.wisconsin'),
        ),
        migrations.RunPython(
            code=share.robot.RobotScheduleMigration('edu.wisconsin'),
        ),
    ]
