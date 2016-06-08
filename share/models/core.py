import enum

import jsonpatch

from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from share.models.util import ZipField

__all__ = ('ShareUser', 'RawData', 'ChangeRequest', 'ChangeStatus')


class ShareUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # short_id = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=50, null=True)
    is_entity = models.BooleanField(default=False)


class RawData(models.Model):
    id = models.AutoField(primary_key=True)
    data = ZipField(blank=False)
    source = models.ForeignKey(ShareUser)
