# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-12-12 15:55
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
import share.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('share', '0011_sitebanner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='abstractagent',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_abstractagent', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='abstractagentrelation',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_abstractagentrelation', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='abstractagentworkrelation',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_abstractagentworkrelation', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='abstractcreativework',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_abstractcreativework', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='abstractworkrelation',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_abstractworkrelation', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='agentidentifier',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_agentidentifier', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='award',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_award', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='extradata',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_extradata', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='tag',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_tag', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='throughawards',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_throughawards', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='throughcontributor',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_throughcontributor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='throughsubjects',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_throughsubjects', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='throughtags',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_throughtags', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='workidentifier',
            name='sources',
            field=share.models.fields.TypedManyToManyField(editable=False, related_name='source_workidentifier', to=settings.AUTH_USER_MODEL),
        ),
    ]
