import zlib
import base64

from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser

from share.models.util import ZipField

__all__ = ('ShareUser', 'RawData')


class ShareUser(AbstractBaseUser):
    USERNAME_FIELD = 'short_id'
    REQUIRED_FIELDS = ('full_name', 'is_entity')

    short_id = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=50, null=True)
    is_entity = models.BooleanField(default=False)


class RawData(models.Model):
    id = models.AutoField(primary_key=True)
    data = ZipField(blank=False)
    source = models.ForeignKey(ShareUser)
